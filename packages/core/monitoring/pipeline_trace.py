"""
In-memory pipeline trace store for LangGraph + RAG debugging.

Records per-request spans (nodes + nested retrieval steps) with sanitized I/O.
Thread-safe ring buffer; not for multi-process production analytics.
"""

from __future__ import annotations

import re
import threading
import time
import uuid
from collections import OrderedDict
from contextvars import ContextVar
from dataclasses import dataclass, field, asdict
from typing import Any, Awaitable, Callable, Dict, List, Optional

from config.settings import settings

_trace_id_var: ContextVar[Optional[str]] = ContextVar("pipeline_trace_id", default=None)


def get_active_trace_id() -> Optional[str]:
    return _trace_id_var.get()


@dataclass
class SpanRecord:
    span_id: str
    name: str
    parent_span_id: Optional[str]
    order: int
    start_ms: float
    end_ms: float
    duration_ms: float
    status: str  # ok | error
    error_message: Optional[str] = None
    input_summary: Dict[str, Any] = field(default_factory=dict)
    output_summary: Dict[str, Any] = field(default_factory=dict)
    feature_tag: Optional[str] = None


@dataclass
class TraceRecord:
    trace_id: str
    tenant_id: str
    user_id: str
    started_at_ms: float
    ended_at_ms: float = 0.0
    total_duration_ms: float = 0.0
    success: bool = True
    spans: List[SpanRecord] = field(default_factory=list)
    _span_seq: int = 0


def _snippet(text: Optional[str], max_chars: Optional[int] = None) -> str:
    if text is None:
        return ""
    s = str(text)
    m = max_chars or getattr(settings, "PIPELINE_TRACE_SNIPPET_CHARS", 800)
    s = re.sub(r"\b[\w._%+-]+@[\w.-]+\.[A-Za-z]{2,}\b", "[email]", s)
    s = re.sub(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "[phone]", s)
    if len(s) > m:
        return s[: m - 3] + "..."
    return s


def sanitize_state_for_trace(
    state: Dict[str, Any],
    *,
    outgoing: bool,
    node_name: str = "",
) -> Dict[str, Any]:
    """Node-specific, privacy-aware snapshot of ChatGraphState for traces."""
    if not state:
        return {}

    _msg = _snippet(state.get("redacted_message") or state.get("message"), 300)
    _hist_len = len(state.get("effective_history") or state.get("history") or [])

    if node_name == "ModerationInput":
        if not outgoing:
            return {"message": _msg, "history_turns": _hist_len}
        return {
            "blocked": state.get("blocked", False),
            "error": _snippet(state.get("error"), 200) if state.get("error") else None,
            "redacted_message": _snippet(state.get("redacted_message"), 300) if state.get("redacted_message") else None,
        }

    if node_name == "Memory":
        if not outgoing:
            return {"raw_history_turns": _hist_len, "message": _msg}
        eff = state.get("effective_history") or []
        has_summary = any(
            (m.get("role") == "system" and "summary" in (m.get("content") or "").lower()[:80])
            for m in eff
        )
        return {
            "effective_history_turns": len(eff),
            "pruned": _hist_len != len(eff),
            "summarized": has_summary,
        }

    if node_name == "CacheCheck":
        if not outgoing:
            return {"message": _msg}
        return {"use_cached_response": state.get("use_cached_response", False)}

    if node_name == "DialogRoute":
        if not outgoing:
            return {"message": _msg}
        return {
            "skip_rag": state.get("skip_rag", False),
            "reason": state.get("dialog_route_reason", ""),
        }

    if node_name == "DirectChat":
        if not outgoing:
            return {"message": _msg}
        return {"answer_preview": _snippet(state.get("final_answer"), 400)}

    if node_name == "IntentClassify":
        if not outgoing:
            return {"message": _msg}
        return {
            "classified_intent": str(state.get("classified_intent", "")),
            "whole_file_summary": state.get("whole_file_summary", False),
        }

    if node_name == "WholeFileMapReduce":
        if not outgoing:
            return {"message": _msg, "active_sources": len(state.get("active_source_ids") or [])}
        return {
            "map_reduce_ok": state.get("map_reduce_ok", False),
            "answer_preview": _snippet(state.get("precomputed_answer"), 300) if state.get("precomputed_answer") else None,
        }

    if node_name == "Retrieval":
        if not outgoing:
            return {
                "query": _msg,
                "classified_intent": str(state.get("classified_intent", "")),
            }
        matches = state.get("matches") or []
        rq = state.get("rewritten_queries") or []
        return {
            "chunks_retrieved": len(matches),
            "rewritten_queries": [_snippet(q, 200) for q in rq[:4]],
            "focused_query": _snippet(state.get("focused_query"), 200),
        }

    if node_name == "ContextSelector":
        if not outgoing:
            matches = state.get("matches") or []
            return {"chunks_in": len(matches)}
        sel = state.get("selected_matches") or []
        return {
            "chunks_selected": len(sel),
            "citation_count": len(state.get("citations") or []),
            "context_chars": len(state.get("context") or ""),
        }

    if node_name == "Generate":
        if not outgoing:
            return {
                "query": _msg,
                "context_chars": len(state.get("context") or ""),
                "citation_count": len(state.get("citations") or []),
            }
        return {"answer_preview": _snippet(state.get("final_answer"), 500)}

    if node_name == "ModerationOutput":
        if not outgoing:
            return {"answer_preview": _snippet(state.get("final_answer"), 300)}
        fot = state.get("final_output_text") or ""
        blocked = fot != (state.get("final_answer") or "")
        return {
            "moderation_passed": not blocked,
            "output_preview": _snippet(fot, 300),
        }

    if node_name == "Evaluator":
        if not outgoing:
            return {"output_preview": _snippet(state.get("final_output_text"), 200)}
        dp = state.get("done_payload") or {}
        return {
            "confidence_score": dp.get("confidence_score"),
            "low_confidence": dp.get("low_confidence", False),
            "trace_id": dp.get("trace_id"),
        }

    # Fallback for any unknown node
    out: Dict[str, Any] = {"message": _msg}
    if outgoing:
        fa = state.get("final_answer") or state.get("final_output_text")
        if fa:
            out["answer_preview"] = _snippet(fa, 400)
    return out


class PipelineTraceStore:
    """Ring buffer of completed traces + in-flight span list for active trace."""

    def __init__(self, max_traces: int = 200):
        self._max = max_traces
        self._lock = threading.Lock()
        self._traces: "OrderedDict[str, TraceRecord]" = OrderedDict()

    def start_trace(self, trace_id: str, tenant_id: str, user_id: str) -> None:
        if not getattr(settings, "ENABLE_PIPELINE_TRACE", True):
            return
        _trace_id_var.set(trace_id)
        now = time.perf_counter() * 1000
        with self._lock:
            self._traces[trace_id] = TraceRecord(
                trace_id=trace_id,
                tenant_id=tenant_id,
                user_id=user_id,
                started_at_ms=now,
            )

    def add_span(
        self,
        name: str,
        duration_ms: float,
        *,
        input_summary: Optional[Dict[str, Any]] = None,
        output_summary: Optional[Dict[str, Any]] = None,
        status: str = "ok",
        error_message: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        feature_tag: Optional[str] = None,
    ) -> str:
        if not getattr(settings, "ENABLE_PIPELINE_TRACE", True):
            return ""
        tid = _trace_id_var.get()
        if not tid:
            return ""
        span_id = str(uuid.uuid4())
        now = time.perf_counter() * 1000
        with self._lock:
            tr = self._traces.get(tid)
            if not tr:
                return ""
            tr._span_seq += 1
            order = tr._span_seq
            start_ms = now - duration_ms
            sp = SpanRecord(
                span_id=span_id,
                name=name,
                parent_span_id=parent_span_id,
                order=order,
                start_ms=start_ms,
                end_ms=now,
                duration_ms=duration_ms,
                status=status,
                error_message=error_message,
                input_summary=dict(input_summary or {}),
                output_summary=dict(output_summary or {}),
                feature_tag=feature_tag,
            )
            tr.spans.append(sp)
        return span_id

    def finalize_trace(self, trace_id: str, *, success: bool = True) -> None:
        if not getattr(settings, "ENABLE_PIPELINE_TRACE", True):
            _trace_id_var.set(None)
            return
        now = time.perf_counter() * 1000
        with self._lock:
            tr = self._traces.get(trace_id)
            if tr:
                tr.ended_at_ms = now
                tr.total_duration_ms = now - tr.started_at_ms
                tr.success = success
                self._traces.move_to_end(trace_id, last=True)
                while len(self._traces) > self._max:
                    self._traces.popitem(last=False)
        _trace_id_var.set(None)

    def get_trace(self, trace_id: str) -> Optional[TraceRecord]:
        with self._lock:
            return self._traces.get(trace_id)

    def list_recent_trace_ids(self, limit: int = 50) -> List[str]:
        with self._lock:
            ids = list(self._traces.keys())
            return list(reversed(ids))[:limit]

    def list_recent_traces_filtered(
        self,
        *,
        user_id: Optional[str],
        limit: int,
    ) -> List[TraceRecord]:
        """
        Newest-first trace records. If user_id is set, only that user's traces;
        if None, all users (for admin).
        """
        lim = max(1, min(int(limit), 200))
        with self._lock:
            out: List[TraceRecord] = []
            for tid in reversed(list(self._traces.keys())):
                tr = self._traces.get(tid)
                if not tr:
                    continue
                if user_id is not None and tr.user_id != user_id:
                    continue
                out.append(tr)
                if len(out) >= lim:
                    break
            return out

    def to_jsonable(self, tr: TraceRecord) -> Dict[str, Any]:
        return {
            "trace_id": tr.trace_id,
            "tenant_id": tr.tenant_id,
            "user_id": tr.user_id,
            "started_at_ms": tr.started_at_ms,
            "ended_at_ms": tr.ended_at_ms,
            "total_duration_ms": tr.total_duration_ms,
            "success": tr.success,
            "spans": [asdict(s) for s in tr.spans],
        }


_store: Optional[PipelineTraceStore] = None


def get_pipeline_trace_store() -> PipelineTraceStore:
    global _store
    if _store is None:
        mx = int(getattr(settings, "PIPELINE_TRACE_MAX_STORED", 200))
        _store = PipelineTraceStore(max_traces=mx)
    return _store


def record_retrieval_span(
    name: str,
    duration_ms: float,
    *,
    input_summary: Optional[Dict[str, Any]] = None,
    output_summary: Optional[Dict[str, Any]] = None,
    status: str = "ok",
    error_message: Optional[str] = None,
    parent_span_id: Optional[str] = None,
    feature_tag: Optional[str] = None,
) -> str:
    """Record a nested step inside Retriever (or similar)."""
    return get_pipeline_trace_store().add_span(
        name,
        duration_ms,
        input_summary=input_summary,
        output_summary=output_summary,
        status=status,
        error_message=error_message,
        parent_span_id=parent_span_id,
        feature_tag=feature_tag,
    )


async def trace_async(
    name: str,
    coro: Awaitable[Any],
    *,
    input_summary: Optional[Dict[str, Any]] = None,
    output_fn: Optional[Callable[[Any], Dict[str, Any]]] = None,
    feature_tag: Optional[str] = None,
) -> Any:
    """Await a coroutine and record one nested span (e.g. inside Retriever)."""
    if not getattr(settings, "ENABLE_PIPELINE_TRACE", True) or not get_active_trace_id():
        return await coro
    t0 = time.perf_counter()
    try:
        r = await coro
        dt = (time.perf_counter() - t0) * 1000
        osum = output_fn(r) if output_fn else {}
        record_retrieval_span(
            name,
            dt,
            input_summary=input_summary or {},
            output_summary=osum,
            feature_tag=feature_tag,
        )
        return r
    except Exception as e:
        dt = (time.perf_counter() - t0) * 1000
        record_retrieval_span(
            name,
            dt,
            input_summary=input_summary or {},
            output_summary={},
            status="error",
            error_message=str(e)[:500],
            feature_tag=feature_tag,
        )
        raise


def trace_snippet(text: Optional[str], max_chars: int = 200) -> str:
    return _snippet(text, max_chars)
