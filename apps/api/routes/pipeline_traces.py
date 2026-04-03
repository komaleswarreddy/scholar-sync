"""
Pipeline trace API (LangGraph + RAG debugger).

Traces are in-memory per process. GET /recent is available to any authenticated user
(their traces only); admins see global recent.
"""

from collections import defaultdict
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from packages.core.database.connection import get_db
from packages.core.monitoring.metrics import get_metrics_collector
from packages.core.monitoring.pipeline_trace import get_pipeline_trace_store
from apps.api.routes.admin import check_admin_role

router = APIRouter()


_AGENT_LABELS: Dict[str, str] = {
    "generate": "Generate",
    "direct_chat": "Direct Chat",
    "intent_classify": "Intent Classify",
    "query_rewrite": "Query Rewriter",
    "chat_summarizer": "Chat Summarizer",
    "whole_file_map": "Whole File Map",
    "whole_file_reduce": "Whole File Reduce",
    "studio_generate": "Studio Generate",
    "embedding": "Embedding",
    "cohere_rerank": "Cohere Rerank",
    "moderation": "Moderation",
    "other": "Other",
}


def _normalize_agent_id(feature_tag: Optional[str]) -> str:
    ft = str(feature_tag or "").strip().lower()
    if not ft:
        return "other"
    if ft in {"chat_langgraph", "chat_langgraph_retry_not_found", "chat_langgraph_retry_incomplete", "chat"}:
        return "generate"
    if ft == "chat_langgraph_direct":
        return "direct_chat"
    if ft == "query_rewriter":
        return "query_rewrite"
    if ft == "intent_classifier":
        return "intent_classify"
    if ft == "embedding":
        return "embedding"
    if ft == "cohere_rerank":
        return "cohere_rerank"
    if ft == "chat_summarizer":
        return "chat_summarizer"
    if ft == "whole_file_map":
        return "whole_file_map"
    if ft == "whole_file_reduce":
        return "whole_file_reduce"
    if ft.startswith("studio_") or "studio" in ft:
        return "studio_generate"
    return "other"


def _extract_trace_text(tr: Any, kind: str) -> str:
    spans = sorted(list(getattr(tr, "spans", []) or []), key=lambda s: ((s.start_ms or 0.0), (s.order or 0)))
    if kind == "query":
        keys = ("message", "query", "raw_query", "query_preview", "raw_focus_snippet")
        for sp in spans:
            data = getattr(sp, "input_summary", {}) or {}
            for key in keys:
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return ""

    output_keys = ("output_preview", "answer_preview")
    for preferred_name in ("ModerationOutput", "Generate", "DirectChat", "WholeFileMapReduce"):
        for sp in reversed(spans):
            if str(getattr(sp, "name", "")) != preferred_name:
                continue
            data = getattr(sp, "output_summary", {}) or {}
            for key in output_keys:
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    return ""


def _collect_trace_usage(trace_id: str, tenant_id: str) -> Dict[str, Any]:
    metrics = get_metrics_collector()
    with metrics._lock:
        calls = list(metrics._llm_calls)

    trace_calls = [
        c
        for c in calls
        if str(c.get("tenant_id")) == str(tenant_id) and str(c.get("request_id") or "") == str(trace_id)
    ]
    trace_calls.sort(key=lambda c: str(c.get("timestamp") or ""))

    grouped: Dict[str, Dict[str, Any]] = {}
    rows: List[Dict[str, Any]] = []
    total_in = total_out = total_tokens = 0
    total_cost = 0.0

    for idx, call in enumerate(trace_calls, start=1):
        feature_tag = str(call.get("feature_tag") or "unknown")
        agent_id = _normalize_agent_id(feature_tag)
        agent_label = _AGENT_LABELS.get(agent_id, "Other")
        prompt_tokens = int(call.get("prompt_tokens") or 0)
        completion_tokens = int(call.get("completion_tokens") or 0)
        tokens_total = int(call.get("total_tokens") or 0)
        cost = float(call.get("cost") or 0.0)
        latency_ms = float(call.get("latency_ms") or 0.0)
        model = str(call.get("model") or "unknown")
        provider = str(call.get("provider") or "unknown")

        rows.append(
            {
                "call_index": idx,
                "timestamp": call.get("timestamp"),
                "agent_id": agent_id,
                "agent_label": agent_label,
                "feature_tag": feature_tag,
                "model": model,
                "provider": provider,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": tokens_total,
                "cost_usd": round(cost, 6),
                "latency_ms": round(latency_ms, 2),
            }
        )

        total_in += prompt_tokens
        total_out += completion_tokens
        total_tokens += tokens_total
        total_cost += cost

        if feature_tag not in grouped:
            grouped[feature_tag] = {
                "agent_id": agent_id,
                "agent_label": agent_label,
                "feature_tag": feature_tag,
                "calls": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_usd": 0.0,
                "latency_ms_total": 0.0,
                "models": defaultdict(int),
                "providers": defaultdict(int),
            }
        row = grouped[feature_tag]
        row["calls"] += 1
        row["prompt_tokens"] += prompt_tokens
        row["completion_tokens"] += completion_tokens
        row["total_tokens"] += tokens_total
        row["cost_usd"] += cost
        row["latency_ms_total"] += latency_ms
        row["models"][model] += 1
        row["providers"][provider] += 1

    usage_by_agent: List[Dict[str, Any]] = []
    for feature_tag, row in grouped.items():
        calls_n = max(int(row["calls"]), 1)
        usage_by_agent.append(
            {
                "agent_id": row["agent_id"],
                "agent_label": row["agent_label"],
                "feature_tag": feature_tag,
                "calls": row["calls"],
                "prompt_tokens": row["prompt_tokens"],
                "completion_tokens": row["completion_tokens"],
                "total_tokens": row["total_tokens"],
                "cost_usd": round(float(row["cost_usd"]), 6),
                "latency_ms_avg": round(float(row["latency_ms_total"]) / calls_n, 2),
                "models": dict(sorted(row["models"].items(), key=lambda x: x[1], reverse=True)),
                "providers": dict(sorted(row["providers"].items(), key=lambda x: x[1], reverse=True)),
            }
        )
    usage_by_agent.sort(key=lambda x: (x["total_tokens"], x["cost_usd"], x["calls"]), reverse=True)

    return {
        "summary": {
            "llm_calls": len(trace_calls),
            "prompt_tokens": total_in,
            "completion_tokens": total_out,
            "total_tokens": total_tokens,
            "cost_usd": round(total_cost, 6),
        },
        "by_agent": usage_by_agent,
        "calls": rows,
    }


def _build_trace_payload(tr: Any) -> Dict[str, Any]:
    payload = get_pipeline_trace_store().to_jsonable(tr)
    payload["trace_summary"] = {
        "query_preview": _extract_trace_text(tr, "query"),
        "response_preview": _extract_trace_text(tr, "response"),
    }
    payload["usage"] = _collect_trace_usage(tr.trace_id, tr.tenant_id)
    return payload


@router.get("/recent")
async def list_recent_traces(
    request: Request,
    db: AsyncSession = Depends(get_db),
    limit: int = 30,
) -> Dict[str, Any]:
    """
    Recent pipeline traces for the authenticated user.
    Admins see global recent traces (all users); regular users only their own.
    """
    if not getattr(settings, "ENABLE_PIPELINE_TRACE", True):
        raise HTTPException(status_code=404, detail="Pipeline tracing disabled")
    uid = getattr(request.state, "user_id", None)
    if not uid:
        raise HTTPException(status_code=401, detail="Authentication required")
    is_admin = await check_admin_role(request, db)
    store = get_pipeline_trace_store()
    # None = no filter (admin); else restrict to caller's Clerk user id
    filter_user: str | None = None if is_admin else uid
    traces = store.list_recent_traces_filtered(user_id=filter_user, limit=min(limit, 100))
    out: List[Dict[str, Any]] = [
        {
            "trace_id": tr.trace_id,
            "user_id": tr.user_id,
            "tenant_id": tr.tenant_id,
            "total_duration_ms": tr.total_duration_ms,
            "success": tr.success,
            "span_count": len(tr.spans),
        }
        for tr in traces
    ]
    return {"traces": out, "scope": "all" if is_admin else "mine"}


@router.get("/{trace_id}")
async def get_pipeline_trace(
    trace_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Return a single trace (owner or admin)."""
    if not getattr(settings, "ENABLE_PIPELINE_TRACE", True):
        raise HTTPException(status_code=404, detail="Pipeline tracing disabled")
    uid = getattr(request.state, "user_id", None)
    if not uid:
        raise HTTPException(status_code=401, detail="Authentication required")
    store = get_pipeline_trace_store()
    tr = store.get_trace(trace_id)
    if not tr:
        raise HTTPException(status_code=404, detail="Trace not found or expired")
    # Owner can always load their trace without hitting the DB for admin role.
    if uid == tr.user_id:
        return _build_trace_payload(tr)
    # Cross-tenant / other-user trace: require admin. If DB is down, return 503 — not a
    # misleading 403 (check_admin_role otherwise returns False when DB errors).
    is_admin = await check_admin_role(request, db, raise_on_db_unavailable=True)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Not allowed to view this trace")
    return _build_trace_payload(tr)
