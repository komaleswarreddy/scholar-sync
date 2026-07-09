from __future__ import annotations

import asyncio
import inspect
import re
import time
import uuid
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Tuple

from config.settings import settings
from packages.core.langgraph.chat_state import ChatGraphState
from packages.core.security import (
    RefusalTemplates,
    RefusalReason,
    SafetyFilter,
    PromptInjectionDetector,
    IntentGate,
    PIIDetector,
    check_moderation,
    detect_cheating_request,
)
from packages.core.security.openai_moderation import (
    is_openai_moderation_configured,
    moderation_indicates_block,
    moderation_indicates_block_output,
)
from packages.core.memory import AnswerCache, ChatSummarizer, MemoryManager
from packages.core.memory.retrieval_session_cache import (
    RetrievalSessionCache,
    build_retrieval_session_key,
)
from packages.core.rag.embedder import Embedder
from packages.core.rag.tutor_relevance import max_relevance_vs_chunks
from packages.core.rag.context_grounding_gate import (
    evaluate_context_grounding,
    extract_chunk_texts_from_matches,
)
from packages.core.rag.retriever import Retriever
from packages.core.rag.agents import (
    ContextDeduper,
    EarlyStopDetector,
    CitationEnforcer,
    OutputLengthLimiter,
    OutputFormatter,
    OutputFormat,
    ContextSelector,
)
from packages.core.prompts import load_prompt
from packages.core.rag.agents.conversation_context import split_summary_and_transcript_for_prompt
from packages.core.llm import get_llm_client, get_model_for_task
from packages.core.evaluation.confidence_scorer import ConfidenceScorer
from packages.core.rag.metadata_query import is_metadata_attribution_query, is_source_scope_meta_query
from packages.core.rag.dialog_router import should_skip_rag
from packages.core.monitoring.pipeline_trace import (
    get_pipeline_trace_store,
    sanitize_state_for_trace,
)
from packages.core.security.prompt_integrity import (
    validate_direct_chat_prompt,
    validate_rag_compiled_prompt,
)


def _split_stream_text(text: str, chunk_size: int = 50) -> List[str]:
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)] if text else []


def _strip_suggested_questions(text: str) -> str:
    """Remove trailing 'Suggested questions' section from chat replies."""
    if not text or not text.strip():
        return (text or "").strip()
    trimmed = text.strip()
    trimmed = re.sub(
        r"\n---?\n+\s*##\s*Suggested questions\b.*",
        "",
        trimmed,
        flags=re.DOTALL | re.IGNORECASE,
    ).strip()
    trimmed = re.sub(
        r"\n+\s*##\s*Suggested questions\b.*",
        "",
        trimmed,
        flags=re.DOTALL | re.IGNORECASE,
    ).strip()
    return trimmed


def _normalize_chat_tagged_response(text: str) -> str:
    """
    Remove legacy <main_answer> / <follow_ups> XML-style wrappers from model output
    so the UI shows clean Markdown without follow-up question sections.
    """
    if not text or not text.strip():
        return (text or "").strip()
    t = text.strip()
    tl = t.lower()
    if "<main_answer>" not in tl and "<follow_ups>" not in tl:
        return _strip_suggested_questions(t)

    main_body: Optional[str] = None
    follow_body: Optional[str] = None

    m_main = re.search(
        r"<main_answer>\s*(.*?)\s*</main_answer>",
        t,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if m_main:
        main_body = m_main.group(1).strip()

    m_follow = re.search(
        r"<follow_ups>\s*(.*?)\s*</follow_ups>",
        t,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if m_follow:
        follow_body = m_follow.group(1).strip()

    if main_body is not None:
        return _strip_suggested_questions(main_body)

    t = re.sub(r"</?main_answer>\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"</?follow_ups>\s*", "", t, flags=re.IGNORECASE)
    return _strip_suggested_questions(t.strip())


def _history_drop_trailing_duplicate_user(
    history: List[Dict[str, Any]],
    current_message: str,
) -> List[Dict[str, Any]]:
    """
    If the client included the current user turn as the last history entry, drop it.
    Prevents double-counting in pruning/summarization and keeps transcript aligned with `message`.
    """
    if not history or not (current_message or "").strip():
        return list(history)
    cur = (current_message or "").strip()
    last = history[-1]
    if str(last.get("role", "")).lower() == "user" and str(last.get("content") or "").strip() == cur:
        return list(history[:-1])
    return list(history)


def _answer_looks_incomplete(text: str) -> bool:
    """Detect cut-off model replies (e.g. ends with 'is' / no terminal punctuation)."""
    s = (text or "").strip()
    if not s:
        return True
    # Short but valid replies (e.g. "Yes.", "DNA.", "Mitochondria.") must NOT trigger a
    # completion retry — that retry often collapses to `Not found in provided sources.`.
    if len(s) >= 3 and s.endswith((".", "!", "?", ":", '"', "'", ")", "]", "}")):
        return False
    if len(s) < 8:
        return True
    if s.endswith((".", "!", "?", ":", '"', "'", ")", "]", "}")):
        return False
    if len(s) < 800 and re.search(
        r"\b(is|are|was|were|the|a|an|as|by|of|for|and|or)\s*$",
        s,
        re.IGNORECASE,
    ):
        return True
    return False


def _is_document_summary_query(q: str) -> bool:
    """Broad document/chapter summary or scope-meta requests need many chunks, not the default small cap."""
    q = (q or "").lower()
    return any(
        p in q
        for p in (
            "summarize",
            "summarise",
            "summary",
            "overview of",
            "whole document",
            "entire document",
            "entire pdf",
            "full pdf",
            "whole pdf",
            "whole book",
            "entire book",
            "this pdf",
            "this document",
            "this file",
            "this chapter",
            "the chapter",
            "main topics",
            "topics covered",
            "topics in my",
            "topics in the",
            "what are the topics",
            "what topics",
            "key topics",
            "key points",
            "selected sources",
            "my selected sources",
            "my sources",
            "what is covered",
            "what's covered",
            "what does this chapter",
            "what does the chapter",
            "chapter cover",
            "chapter about",
            "outline of",
            "these documents",
            "those documents",
            "two documents",
            "those two",
            "what are those",
            "what are these",
            "sources about",
            "source about",
            "what is this about",
            "what are they about",
        )
    )


def _query_strings_for_grounding(state: ChatGraphState) -> List[str]:
    """All user/retrieval query variants used for summary and grounding exemptions."""
    parts: List[Any] = [
        state.get("message"),
        state.get("redacted_message"),
        state.get("rewritten_query"),
        state.get("primary_retrieval_query"),
    ]
    rqs = state.get("rewritten_queries") or []
    if isinstance(rqs, list):
        parts.extend(rqs)
    out: List[str] = []
    seen: set[str] = set()
    for p in parts:
        s = str(p or "").strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _is_document_summary_query_from_state(state: ChatGraphState) -> bool:
    return any(_is_document_summary_query(q) for q in _query_strings_for_grounding(state))


def _ncert_global_merge_allowed(state: ChatGraphState) -> bool:
    """
    NCERT global merge is allowed when the checkbox is on and either:
    - no user uploads are selected (NCERT-only chat), or
    - tutor scope filters (class/subject/chapter) lock the retrieval namespace.
    Exploratory notebooks with selected uploads stay source-only unless scoped.
    """
    if not bool(state.get("include_ncert_global")):
        return False
    if not getattr(settings, "ENABLE_NCERT_GLOBAL_IN_CHAT", False):
        return False
    active = list(state.get("active_source_ids") or [])
    if not active:
        return True
    if state.get("ncert_class") is None:
        return False
    if not str(state.get("ncert_subject") or "").strip():
        return False
    if state.get("ncert_chapter_no") is None and not str(state.get("ncert_chapter_name") or "").strip():
        return False
    return True


def _filter_matches_to_active_sources(
    matches: List[Dict[str, Any]],
    active_source_ids: List[Any],
) -> List[Dict[str, Any]]:
    if not active_source_ids:
        return matches
    allowed = {str(sid) for sid in active_source_ids if sid}
    if not allowed:
        return matches
    filtered: List[Dict[str, Any]] = []
    for m in matches or []:
        if not isinstance(m, dict):
            continue
        md = m.get("metadata") or {}
        sid = str((md.get("source_id") if isinstance(md, dict) else None) or "")
        if sid in allowed:
            filtered.append(m)
    return filtered


def _is_source_scope_meta_from_state(state: ChatGraphState) -> bool:
    return any(is_source_scope_meta_query(q) for q in _query_strings_for_grounding(state))


def _output_format_for_intent(intent_label: str) -> OutputFormat:
    il = (intent_label or "").lower()
    if il in ("definition", "explanation", "question", "how_to", "qa", "factual"):
        return OutputFormat.BULLET_POINTS
    if il in ("summary", "analysis", "comparison", "compare"):
        return OutputFormat.PARAGRAPH
    return OutputFormat.BULLET_POINTS


def _require_langgraph():
    try:
        from langgraph.graph import StateGraph, END  # noqa: F401
    except Exception as e:  # pragma: no cover
        raise ValueError("LangGraph not installed. Install with: pip install langgraph") from e


class LangGraphChatPipeline:
    """
    Plan B: LangGraph-orchestrated chat pipeline.

    NOTE: To keep endpoint/SSE contract stable, this pipeline returns an async
    generator yielding {"event": ..., "data": ...} dicts.
    """

    def __init__(self, tenant_id: str, user_id: str, db: Any | None = None):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.db = db

        # Set for the duration of a `stream()` call; lets `_node_generate` push live
        # tokens for the primary answer out to the SSE consumer as they are produced,
        # instead of the whole graph having to finish before anything is sent. `None`
        # outside of `stream()` (e.g. in unit tests that call nodes directly), in which
        # case generation falls back to the previous buffered `.generate()` call.
        self._live_stream_queue: Optional[asyncio.Queue] = None

        _require_langgraph()

        # Shared helpers
        self.refusals = RefusalTemplates()
        self.safety_filter = SafetyFilter(strict_mode=settings.SAFETY_STRICT_MODE, block_threshold=0.7)
        self.injection_detector = PromptInjectionDetector(
            strict_mode=settings.SAFETY_STRICT_MODE,
            detection_threshold=settings.INJECTION_DETECTION_THRESHOLD,
        )
        self.intent_gate = IntentGate(
            strict_mode=settings.SAFETY_STRICT_MODE,
            academic_threshold=settings.INTENT_ACADEMIC_THRESHOLD,
        )
        self.pii_detector = PIIDetector(redact_mode=True)
        self.answer_cache = (
            AnswerCache(
                cache_dir=f"cache/answers/{tenant_id}",
                default_ttl_seconds=settings.ANSWER_CACHE_TTL_SECONDS,
                max_cache_size=1000,
            )
            if settings.USE_SESSION_MEMORY and settings.ENABLE_ANSWER_CACHE
            else None
        )
        self.chat_summarizer = (
            ChatSummarizer(
                recent_window=settings.CHAT_KEEP_RECENT,
                summarize_after=settings.CHAT_SUMMARIZE_AFTER,
                max_summary_length=500,
            )
            if settings.USE_SESSION_MEMORY and settings.ENABLE_CHAT_SUMMARIZATION
            else None
        )
        self.memory_manager = (
            MemoryManager(
                max_history_messages=settings.MAX_HISTORY_MESSAGES,
                max_history_tokens=settings.MAX_HISTORY_TOKENS,
                keep_recent=settings.CHAT_KEEP_RECENT,
                prune_strategy=settings.MEMORY_PRUNING_STRATEGY,
            )
            if settings.USE_SESSION_MEMORY and settings.ENABLE_MEMORY_PRUNING
            else None
        )

        self.retriever = Retriever(tenant_id, user_id=user_id)
        self.retrieval_session_cache = RetrievalSessionCache(tenant_id, user_id=user_id)

        self.confidence_scorer = (
            ConfidenceScorer(
                low_threshold=settings.CONFIDENCE_LOW_THRESHOLD,
                high_threshold=settings.CONFIDENCE_HIGH_THRESHOLD,
            )
            if settings.ENABLE_CONFIDENCE_THRESHOLDING
            else None
        )

        # Output agents
        self.early_stop = EarlyStopDetector(enabled=settings.USE_EARLY_STOP, min_length=50)
        self.length_limiter = OutputLengthLimiter(
            max_tokens=settings.MAX_OUTPUT_TOKENS or settings.CHAT_MAX_TOKENS,
            max_characters=settings.MAX_OUTPUT_CHARACTERS,
            max_sentences=settings.MAX_OUTPUT_SENTENCES,
            hard_limit=True,
        )
        fmt_map = {
            "bullet_points": OutputFormat.BULLET_POINTS,
            "numbered_list": OutputFormat.NUMBERED_LIST,
            "paragraph": OutputFormat.PARAGRAPH,
            "structured": OutputFormat.STRUCTURED,
        }
        self.formatter = OutputFormatter(
            default_format=fmt_map.get(settings.DEFAULT_OUTPUT_FORMAT, OutputFormat.BULLET_POINTS),
            use_headings=True,
            max_items=10,
        )
        self.citation_enforcer = CitationEnforcer(strict_mode=True) if settings.ENFORCE_CITATIONS else None
        self.context_selector = ContextSelector(
            max_context_chunks=settings.MAX_CONTEXT_CHUNKS,
            min_relevance_score=settings.SIMILARITY_THRESHOLD,
        )
        self.embedder = Embedder(tenant_id, user_id=user_id)

        # Build LangGraph state machine (Plan B orchestration).
        from langgraph.graph import StateGraph, END

        g: StateGraph = StateGraph(ChatGraphState)
        tw = self._trace_wrap
        g.add_node("ModerationInput", tw("ModerationInput", self._node_moderation_input))
        g.add_node("Memory", tw("Memory", self._node_memory))
        g.add_node("CacheCheck", tw("CacheCheck", self._node_cache))
        g.add_node("DialogRoute", tw("DialogRoute", self._node_dialog_route))
        g.add_node("DirectChat", tw("DirectChat", self._node_direct_chat))
        g.add_node("IntentClassify", tw("IntentClassify", self._node_intent_classify))
        g.add_node("WholeFileMapReduce", tw("WholeFileMapReduce", self._node_whole_file_map_reduce))
        g.add_node("Retrieval", tw("Retrieval", self._node_retrieval))
        g.add_node("ContextSelector", tw("ContextSelector", self._node_context_select))
        g.add_node(
            "ContextGroundingGate",
            tw("ContextGroundingGate", self._node_context_grounding_gate),
        )
        g.add_node("TutorRelevanceGate", tw("TutorRelevanceGate", self._node_tutor_relevance_gate))
        g.add_node("SourceRelevanceGate", tw("SourceRelevanceGate", self._node_source_relevance_gate))
        g.add_node("Generate", tw("Generate", self._node_generate))
        g.add_node("ModerationOutput", tw("ModerationOutput", self._node_moderation_output))
        g.add_node("Evaluator", tw("Evaluator", self._node_eval))

        g.set_entry_point("ModerationInput")

        def _route_after_moderation(s: ChatGraphState) -> str:
            return END if s.get("blocked") else "Memory"

        g.add_conditional_edges("ModerationInput", _route_after_moderation, {END: END, "Memory": "Memory"})
        g.add_edge("Memory", "CacheCheck")

        def _route_after_cache(s: ChatGraphState) -> str:
            return END if s.get("use_cached_response") else "DialogRoute"

        g.add_conditional_edges(
            "CacheCheck",
            _route_after_cache,
            {END: END, "DialogRoute": "DialogRoute"},
        )

        def _route_after_dialog(s: ChatGraphState) -> str:
            return "DirectChat" if s.get("skip_rag") else "IntentClassify"

        g.add_conditional_edges(
            "DialogRoute",
            _route_after_dialog,
            {"DirectChat": "DirectChat", "IntentClassify": "IntentClassify"},
        )

        g.add_edge("DirectChat", "ModerationOutput")

        def _route_after_intent(s: ChatGraphState) -> str:
            # LLM intent layer: policy / prompt-injection — skip RAG and emit refusal via ModerationOutput.
            if str(s.get("classified_intent") or "").strip().lower() == "security_block" and getattr(
                settings, "ENABLE_INTENT_SECURITY_BLOCK", True
            ):
                return "ModerationOutput"
            # Forced map-reduce (e.g. post-upload auto-summary): must not short-circuit to DirectChat.
            active_ids = s.get("active_source_ids") or []
            forced = (
                bool(s.get("force_whole_file_map_reduce"))
                and len(active_ids) == 1
                and getattr(settings, "USE_WHOLE_FILE_MAP_REDUCE", True)
                and bool(s.get("whole_file_summary"))
            )
            if forced:
                return "WholeFileMapReduce"
            # Conversational / chat-only intents should bypass retrieval entirely.
            ci = str(s.get("classified_intent") or "").strip().lower()
            if ci in {"conversational", "chat_only"} or s.get("skip_rag"):
                return "DirectChat"
            return "WholeFileMapReduce" if s.get("whole_file_summary") else "Retrieval"

        g.add_conditional_edges(
            "IntentClassify",
            _route_after_intent,
            {
                "ModerationOutput": "ModerationOutput",
                "DirectChat": "DirectChat",
                "WholeFileMapReduce": "WholeFileMapReduce",
                "Retrieval": "Retrieval",
            },
        )

        def _route_after_whole_file(s: ChatGraphState) -> str:
            return "Generate" if s.get("map_reduce_ok") else "Retrieval"

        g.add_conditional_edges(
            "WholeFileMapReduce",
            _route_after_whole_file,
            {"Generate": "Generate", "Retrieval": "Retrieval"},
        )

        g.add_edge("Retrieval", "ContextSelector")
        g.add_node("TwoStageGrounding", tw("TwoStageGrounding", self._node_two_stage_grounding))
        g.add_edge("ContextSelector", "TwoStageGrounding")
        g.add_edge("TwoStageGrounding", "ContextGroundingGate")

        def _route_after_context_grounding(s: ChatGraphState) -> str:
            return "ModerationOutput" if s.get("context_grounding_blocked") else "TutorRelevanceGate"

        g.add_conditional_edges(
            "ContextGroundingGate",
            _route_after_context_grounding,
            {"ModerationOutput": "ModerationOutput", "TutorRelevanceGate": "TutorRelevanceGate"},
        )

        def _route_after_tutor_relevance_gate(s: ChatGraphState) -> str:
            return "ModerationOutput" if s.get("tutor_generation_blocked") else "SourceRelevanceGate"

        g.add_conditional_edges(
            "TutorRelevanceGate",
            _route_after_tutor_relevance_gate,
            {"ModerationOutput": "ModerationOutput", "SourceRelevanceGate": "SourceRelevanceGate"},
        )

        def _route_after_source_relevance_gate(s: ChatGraphState) -> str:
            return "ModerationOutput" if s.get("source_relevance_blocked") else "Generate"

        g.add_conditional_edges(
            "SourceRelevanceGate",
            _route_after_source_relevance_gate,
            {"ModerationOutput": "ModerationOutput", "Generate": "Generate"},
        )
        g.add_edge("Generate", "ModerationOutput")
        g.add_edge("ModerationOutput", "Evaluator")
        g.add_node("CacheStore", tw("CacheStore", self._node_cache_store))
        g.add_edge("Evaluator", "CacheStore")
        g.add_edge("CacheStore", END)

        self._graph = g.compile()

    def _trace_wrap(self, name: str, fn: Callable[..., Any]) -> Callable[..., Any]:
        """Record duration + sanitized state snapshots for the pipeline debugger."""
        store = get_pipeline_trace_store()
        if not getattr(settings, "ENABLE_PIPELINE_TRACE", True):
            return fn

        if inspect.iscoroutinefunction(fn):

            async def async_wrapped(state: ChatGraphState) -> ChatGraphState:
                inp = sanitize_state_for_trace(dict(state), outgoing=False, node_name=name)
                t0 = time.perf_counter()
                try:
                    out = await fn(state)
                    dt = (time.perf_counter() - t0) * 1000
                    store.add_span(
                        name,
                        dt,
                        input_summary=inp,
                        output_summary=sanitize_state_for_trace(dict(out), outgoing=True, node_name=name),
                        status="ok",
                    )
                    return out
                except Exception as e:
                    dt = (time.perf_counter() - t0) * 1000
                    store.add_span(
                        name,
                        dt,
                        input_summary=inp,
                        output_summary={},
                        status="error",
                        error_message=str(e)[:500],
                    )
                    raise

            return async_wrapped

        def sync_wrapped(state: ChatGraphState) -> ChatGraphState:
            inp = sanitize_state_for_trace(dict(state), outgoing=False, node_name=name)
            t0 = time.perf_counter()
            try:
                out = fn(state)
                dt = (time.perf_counter() - t0) * 1000
                store.add_span(
                    name,
                    dt,
                    input_summary=inp,
                    output_summary=sanitize_state_for_trace(dict(out), outgoing=True, node_name=name),
                    status="ok",
                )
                return out
            except Exception as e:
                dt = (time.perf_counter() - t0) * 1000
                store.add_span(
                    name,
                    dt,
                    input_summary=inp,
                    output_summary={},
                    status="error",
                    error_message=str(e)[:500],
                )
                raise

        return sync_wrapped

    def _push_live(self, item: Tuple[str, Any]) -> None:
        """Best-effort push of a live-stream event onto the current request's queue.

        Never raises: if there is no active `stream()` consumer (queue is None) or the
        queue rejects the item for some reason, generation must proceed unaffected —
        live streaming is a UX optimization, not a correctness requirement.
        """
        q = self._live_stream_queue
        if q is None:
            return
        try:
            q.put_nowait(item)
        except Exception:
            pass

    async def _run_graph_and_signal(self, state: ChatGraphState, queue: asyncio.Queue) -> None:
        """Run the compiled graph to completion and post the outcome onto `queue`.

        Runs as a background task so `stream()` can concurrently drain live tokens
        pushed by `_node_generate` while the rest of the graph (including nodes that
        run after Generate, like ModerationOutput) executes normally.
        """
        try:
            result = await self._graph.ainvoke(state)
            await queue.put(("__graph_done__", result))
        except Exception as exc:  # noqa: BLE001 - re-raised by the consumer in stream()
            await queue.put(("__graph_error__", exc))

    def _moderation_refusal(self) -> str:
        return self.refusals.get_refusal(RefusalReason.SAFETY_VIOLATION, variation_key=self.user_id)

    def _prompt_injection_refusal_message(self) -> str:
        m = (getattr(settings, "PROMPT_INJECTION_REFUSAL_MESSAGE", "") or "").strip()
        return m or self.refusals.get_refusal(RefusalReason.PROMPT_INJECTION, variation_key=self.user_id)

    def _merge_guardrails_trace(self, state: ChatGraphState) -> None:
        if not getattr(settings, "ENABLE_PIPELINE_TRACE", True):
            return
        get_pipeline_trace_store().merge_artifact(
            "guardrails",
            {
                "prompt_injection_detected": bool(state.get("prompt_injection_detected", False)),
                "injection_pattern_matched": state.get("injection_pattern_matched"),
                "generation_blocked_reason": (state.get("generation_blocked_reason") or None),
            },
        )

    async def _record_guardrail_block_event(self, reason: str, session_id: Optional[str] = None) -> None:
        """
        Best-effort persistence for security dashboard tables.
        - guardrail_user_blocks: increment per user+tenant
        - alert_user_sessions: append alert rows for blocked events
        """
        try:
            from sqlalchemy import select
            from packages.core.database.connection import db_session
            from packages.core.database.models.guardrail_user_block import GuardrailUserBlock
            from packages.core.database.models.alert_user_session import AlertUserSession

            tenant_uuid = uuid.UUID(self.tenant_id)
            session_uuid = None
            if session_id:
                try:
                    session_uuid = uuid.UUID(session_id)
                except Exception:
                    session_uuid = None

            async with db_session() as db:
                existing = await db.execute(
                    select(GuardrailUserBlock).where(
                        GuardrailUserBlock.tenant_id == tenant_uuid,
                        GuardrailUserBlock.user_id == self.user_id,
                    )
                )
                row = existing.scalar_one_or_none()
                if row:
                    row.block_count = int(row.block_count or 0) + 1
                    row.block_reason = reason[:120]
                    if session_uuid:
                        row.session_id = session_uuid
                else:
                    row = GuardrailUserBlock(
                        tenant_id=tenant_uuid,
                        user_id=self.user_id,
                        user_name=self.user_id,
                        session_id=session_uuid,
                        block_count=1,
                        block_reason=reason[:120],
                    )
                    db.add(row)

                db.add(
                    AlertUserSession(
                        tenant_id=tenant_uuid,
                        user_id=self.user_id,
                        session_id=session_uuid,
                        alert_type="guardrail_block",
                        alert_message=reason[:400],
                        severity="medium",
                    )
                )
                await db.commit()
        except Exception:
            pass

    async def _load_source_titles(self, source_ids: List[str]) -> Dict[str, str]:
        """
        Best-effort lookup of source_id -> title from DB, matching existing chat behavior.
        Uses a short-lived session so SSE streams do not hold pool connections.
        """
        if not source_ids:
            return {}
        try:
            import uuid as uuid_lib
            from sqlalchemy import select
            from packages.core.database.connection import db_session
            from packages.core.database.models.source import Source
            from packages.core.database.models.ncert_global import NcertGlobalDocument

            tenant_uuid = uuid_lib.UUID(self.tenant_id)
            source_uuids = []
            for sid in source_ids:
                try:
                    source_uuids.append(uuid_lib.UUID(sid))
                except Exception:
                    continue
            if not source_uuids:
                return {}
            async with db_session() as db:
                result = await db.execute(
                    select(Source.id, Source.title).where(
                        Source.id.in_(source_uuids),
                        Source.tenant_id == tenant_uuid,
                        Source.user_id == self.user_id,
                    )
                )
                title_map = {str(r.id): r.title for r in result.all() if r and r.title}

                unresolved = [sid for sid in source_uuids if str(sid) not in title_map]
                if unresolved:
                    global_result = await db.execute(
                        select(
                            NcertGlobalDocument.id,
                            NcertGlobalDocument.title,
                            NcertGlobalDocument.class_num,
                            NcertGlobalDocument.subject,
                        ).where(NcertGlobalDocument.id.in_(unresolved))
                    )
                    for row in global_result.all():
                        if not row:
                            continue
                        title = row.title
                        if not title:
                            subject = str(row.subject or "").replace("_", " ").title().strip()
                            title = f"NCERT Class {row.class_num} {subject}".strip()
                        if title:
                            title_map[str(row.id)] = title

                return title_map
        except Exception:
            return {}

    async def _node_moderation_input(self, state: ChatGraphState) -> ChatGraphState:
        text = state.get("message", "")
        state["prompt_injection_detected"] = False
        state["injection_pattern_matched"] = None

        # Diagram order: PII -> injection -> intent gate -> safety; then OpenAI moderation API.
        if settings.ENABLE_PII_DETECTION:
            redacted, pii = self.pii_detector.redact(text)
            if pii.get("has_pii"):
                state["blocked"] = True
                state["error"] = self.refusals.get_refusal(RefusalReason.PII_DETECTED, variation_key=self.user_id)
                self._merge_guardrails_trace(state)
                return state
            text = redacted

        if settings.ENABLE_INJECTION_DETECTION:
            inj = self.injection_detector.detect(text)
            if not inj.get("is_injection") and getattr(
                settings, "ENABLE_PROMPT_INJECTION_EMBEDDING_SIM", False
            ):
                emb = await self.injection_detector.detect_with_embedding_guard(text, self.embedder)
                if emb.get("is_injection"):
                    inj = emb
            if inj.get("is_injection"):
                state["blocked"] = True
                state["error"] = self._prompt_injection_refusal_message()
                state["prompt_injection_detected"] = True
                state["injection_pattern_matched"] = inj.get("injection_pattern_matched") or inj.get(
                    "message"
                )
                state["generation_blocked_reason"] = "PROMPT_INJECTION"
                self._merge_guardrails_trace(state)
                return state

        from packages.core.security.youth_distress import (
            detect_youth_distress,
            get_supportive_distress_message,
        )

        distress = detect_youth_distress(text)
        if distress.get("is_distress"):
            state["blocked"] = True
            state["error"] = get_supportive_distress_message()
            state["generation_blocked_reason"] = "YOUTH_DISTRESS_SUPPORT"
            self._merge_guardrails_trace(state)
            return state

        if settings.ENABLE_INTENT_GATE:
            intent = self.intent_gate.check_and_block(text)
            if intent.get("blocked"):
                state["blocked"] = True
                state["error"] = (
                    intent.get("message")
                    or self.refusals.get_refusal(RefusalReason.ACADEMIC_ONLY, variation_key=self.user_id)
                )
                self._merge_guardrails_trace(state)
                return state

        cheating = detect_cheating_request(text)
        if cheating.get("is_cheating"):
            state["blocked"] = True
            state["error"] = self.refusals.get_refusal(RefusalReason.ACADEMIC_INTEGRITY, variation_key=self.user_id)
            state["generation_blocked_reason"] = "ACADEMIC_INTEGRITY"
            self._merge_guardrails_trace(state)
            return state

        if settings.ENABLE_SAFETY_FILTERS:
            safe = self.safety_filter.check_input(text, context="academic")
            if safe.get("blocked"):
                state["blocked"] = True
                state["error"] = self.refusals.get_refusal(RefusalReason.INAPPROPRIATE_CONTENT, variation_key=self.user_id)
                self._merge_guardrails_trace(state)
                return state

        try:
            res = check_moderation(text)
            if moderation_indicates_block(res):
                state["blocked"] = True
                state["error"] = self.refusals.get_refusal(RefusalReason.INAPPROPRIATE_CONTENT, variation_key=self.user_id)
                self._merge_guardrails_trace(state)
                return state
        except ValueError as e:
            msg = str(e).lower()
            if "not configured" in msg or "not installed" in msg:
                pass
            elif is_openai_moderation_configured() and not settings.MODERATION_FAIL_OPEN_ON_ERROR:
                state["blocked"] = True
                state["error"] = self.refusals.get_refusal(RefusalReason.GENERAL, variation_key=self.user_id)
                self._merge_guardrails_trace(state)
                return state
        except Exception:
            if is_openai_moderation_configured() and not settings.MODERATION_FAIL_OPEN_ON_ERROR:
                state["blocked"] = True
                state["error"] = self.refusals.get_refusal(RefusalReason.GENERAL, variation_key=self.user_id)
                self._merge_guardrails_trace(state)
                return state

        state["redacted_message"] = text
        state["blocked"] = False
        self._merge_guardrails_trace(state)
        return state

    def _redact_history_contents(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply the same PII redaction as the current turn so past messages do not leak into prompts."""
        if not settings.ENABLE_PII_DETECTION:
            return history
        out: List[Dict[str, Any]] = []
        for msg in history:
            row = dict(msg)
            content = row.get("content")
            if isinstance(content, str) and content.strip():
                redacted, _ = self.pii_detector.redact(content)
                row["content"] = redacted
            out.append(row)
        return out

    def _node_memory(self, state: ChatGraphState) -> ChatGraphState:
        history: List[Dict[str, Any]] = list(state.get("history", []) or [])
        message = state.get("redacted_message") or state.get("message") or ""

        history = _history_drop_trailing_duplicate_user(history, message)
        history = self._redact_history_contents(history)

        if self.memory_manager:
            prune_result = self.memory_manager.prune_history(history, message)
            history = prune_result.get("pruned_history", history)

        if self.chat_summarizer and self.chat_summarizer.should_summarize(history):
            summary_result = self.chat_summarizer.summarize_history(history, message)
            if summary_result.get("was_summarized"):
                history = summary_result.get("summarized_history", history)

        state["effective_history"] = history
        return state

    def _node_cache(self, state: ChatGraphState) -> ChatGraphState:
        if not self.answer_cache:
            state["use_cached_response"] = False
            return state
        if (
            state.get("include_ncert_global")
            and getattr(settings, "ENABLE_NCERT_GLOBAL_IN_CHAT", False)
            and getattr(settings, "TUTOR_NCERT_BYPASS_ANSWER_CACHE", True)
        ):
            state["use_cached_response"] = False
            return state
        if (
            (state.get("active_source_ids") or [])
            and not (
                bool(state.get("include_ncert_global"))
                and getattr(settings, "ENABLE_NCERT_GLOBAL_IN_CHAT", False)
            )
            and getattr(settings, "CHAT_SELECTED_SOURCES_RELEVANCE_GATE_ENABLED", True)
            and getattr(settings, "CHAT_SELECTED_SOURCES_BYPASS_ANSWER_CACHE", True)
        ):
            state["use_cached_response"] = False
            return state
        q = state.get("redacted_message") or state.get("message") or ""
        source_ids = state.get("active_source_ids") or []
        cache_extra = ""
        if state.get("include_ncert_global"):
            cache_extra = (
                f"ncert_v3|{state.get('ncert_class')}|{state.get('ncert_subject')}|"
                f"{state.get('ncert_chapter_no')}|{state.get('ncert_chapter_name')}"
            )
        cached = self.answer_cache.get(q, source_ids, self.tenant_id, cache_extra=cache_extra)
        if cached:
            state["use_cached_response"] = True
            state["cached_answer"] = _normalize_chat_tagged_response(
                (cached.get("answer", "") or "").strip()
            )
            state["cached_citations"] = cached.get("citations", []) or []
        else:
            state["use_cached_response"] = False
        return state

    def _node_dialog_route(self, state: ChatGraphState) -> ChatGraphState:
        """
        Cheap router: small talk / acknowledgments skip Pinecone + hybrid retrieval.
        """
        active_ids = state.get("active_source_ids") or []
        if (
            bool(state.get("force_whole_file_map_reduce"))
            and len(active_ids) == 1
            and getattr(settings, "USE_WHOLE_FILE_MAP_REDUCE", True)
        ):
            state["skip_rag"] = False
            state["dialog_route_reason"] = "force_whole_file_map_reduce"
            return state
        if not getattr(settings, "ENABLE_DIALOG_ROUTER", True):
            state["skip_rag"] = False
            state["dialog_route_reason"] = "router_disabled"
            return state
        msg = state.get("redacted_message") or state.get("message") or ""
        route = should_skip_rag(msg)
        state["skip_rag"] = route.skip_rag
        state["dialog_route_reason"] = route.reason
        if route.skip_rag:
            state["matches"] = []
            state["selected_matches"] = []
            state["context"] = ""
            state["citations"] = []
            state["rewritten_queries"] = []
            state["rewritten_query"] = ""
            state["primary_retrieval_query"] = ""
            state["focused_query"] = ""
            state["classified_intent"] = "chat_only"
        return state

    async def _node_direct_chat(self, state: ChatGraphState) -> ChatGraphState:
        """LLM reply without document retrieval (greetings, thanks, light chat)."""
        message = state.get("redacted_message") or state.get("message") or ""
        conv_hist = state.get("effective_history") or state.get("history") or []
        chat_rolling_summary, conversation_transcript = split_summary_and_transcript_for_prompt(
            conv_hist,
            max_messages=getattr(settings, "CHAT_PROMPT_MAX_HISTORY_MESSAGES", 16),
            max_chars_per_message=getattr(settings, "CHAT_PROMPT_MAX_CHARS_PER_MESSAGE", 900),
        )
        has_chat_summary = bool((chat_rolling_summary or "").strip())
        has_prior_conversation = bool(
            (conversation_transcript or "").strip() or has_chat_summary
        )
        try:
            from packages.core.knowledge.policy_loader import build_chat_policy_block

            chat_policy_block = build_chat_policy_block()
        except Exception:
            chat_policy_block = ""

        full_prompt = load_prompt(
            "chat/direct_chat.j2",
            message=message,
            conversation_transcript=conversation_transcript,
            has_prior_conversation=has_prior_conversation,
            chat_rolling_summary=chat_rolling_summary,
            has_chat_summary=has_chat_summary,
            chat_policy_block=chat_policy_block,
        )
        if getattr(settings, "ENABLE_PROMPT_INTEGRITY_CHECK", True):
            ok_dc, reason_dc = validate_direct_chat_prompt(full_prompt)
            if not ok_dc:
                state["full_prompt"] = f"[prompt_integrity:{reason_dc}]"
                state["final_answer"] = self._prompt_injection_refusal_message()
                state["prompt_injection_detected"] = False
                state["injection_pattern_matched"] = f"compiled_prompt:{reason_dc}"
                state["generation_blocked_reason"] = "PROMPT_INTEGRITY"
                self._merge_guardrails_trace(state)
                return state
        state["full_prompt"] = full_prompt

        provider, model = get_model_for_task("chat")
        llm_client = get_llm_client(provider=provider, model=model, temperature=0.35)
        max_direct = min(512, int(getattr(settings, "CHAT_MAX_TOKENS", 2048) or 2048))
        resp = await llm_client.generate(
            prompt=full_prompt,
            temperature=0.35,
            max_tokens=max_direct,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            feature_tag="chat_langgraph_direct",
        )
        state["final_answer"] = _normalize_chat_tagged_response((resp.content or "").strip())
        return state

    async def _node_intent_classify(self, state: ChatGraphState) -> ChatGraphState:
        from packages.core.rag.agents import IntentClassifier
        from packages.core.rag.whole_file_map_reduce import should_whole_file_map_reduce

        msg = state.get("redacted_message") or state.get("message") or ""
        active = state.get("active_source_ids") or []
        ic = IntentClassifier(self.tenant_id, user_id=self.user_id)
        r = await ic.classify_intent(msg, state.get("effective_history") or state.get("history"))
        intent = r.get("intent")
        intent_label = (getattr(intent, "value", str(intent)) if intent else "").strip().lower()
        state["classified_intent"] = intent_label
        state["scope"] = str(r.get("scope") or "unspecified").strip().lower() or "unspecified"
        state["requires_retrieval"] = bool(r.get("requires_retrieval", True))
        state["requires_attachment"] = bool(r.get("requires_attachment", False))
        try:
            state["intent_classification_confidence"] = float(r.get("confidence", 0.5) or 0.5)
        except (TypeError, ValueError):
            state["intent_classification_confidence"] = 0.5

        if intent_label == "security_block":
            if not getattr(settings, "ENABLE_INTENT_SECURITY_BLOCK", True):
                from packages.core.rag.agents.intent_classifier import UserIntent as _UserIntent

                intent = _UserIntent.GENERAL
                intent_label = "general"
                state["classified_intent"] = "general"
            else:
                state["skip_rag"] = True
                state["dialog_route_reason"] = "intent_classifier_security_block"
                state["matches"] = []
                state["selected_matches"] = []
                state["context"] = ""
                state["citations"] = []
                state["rewritten_queries"] = []
                state["rewritten_query"] = ""
                state["primary_retrieval_query"] = ""
                state["focused_query"] = ""
                state["whole_file_summary"] = False
                state["final_answer"] = self._prompt_injection_refusal_message()
                state["prompt_injection_detected"] = True
                state["injection_pattern_matched"] = "intent_classifier:security_block"
                state["generation_blocked_reason"] = "INTENT_SECURITY_BLOCK"
                self._merge_guardrails_trace(state)
                return state

        if intent_label in {"conversational", "chat_only"}:
            state["skip_rag"] = True
            state["dialog_route_reason"] = "intent_classifier_conversational"
            state["matches"] = []
            state["selected_matches"] = []
            state["context"] = ""
            state["citations"] = []
            state["rewritten_queries"] = []
            state["rewritten_query"] = ""
            state["primary_retrieval_query"] = ""
            state["focused_query"] = ""
        state["whole_file_summary"] = should_whole_file_map_reduce(msg, active, intent)
        if (
            bool(state.get("force_whole_file_map_reduce"))
            and len(active) == 1
            and getattr(settings, "USE_WHOLE_FILE_MAP_REDUCE", True)
        ):
            state["whole_file_summary"] = True
            state["skip_rag"] = False
            state["classified_intent"] = "whole_document_summary"
        return state

    async def _node_whole_file_map_reduce(self, state: ChatGraphState) -> ChatGraphState:
        from packages.core.rag.whole_file_map_reduce import run_whole_file_map_reduce

        msg = state.get("redacted_message") or state.get("message") or ""
        active = state.get("active_source_ids") or []
        res = await run_whole_file_map_reduce(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            message=msg,
            active_source_ids=active,
        )
        pa = (res.get("precomputed_answer") or "").strip()
        if pa:
            state["precomputed_answer"] = pa
            state["context"] = (res.get("section_summaries") or "")[:12000]
            chunks = list(res.get("source_chunks") or [])
            cap = int(getattr(settings, "DOCUMENT_SUMMARY_MAX_CONTEXT_CHUNKS", 12))
            selected = chunks[: max(1, cap)] if chunks else []
            state["selected_matches"] = selected
            if selected:
                prepared = self._prepare_selected_matches(
                    selected,
                    msg,
                    await self._load_source_titles(active),
                )
                _, citations = self._pack_context_from_matches(prepared)
                state["citations"] = citations
            else:
                state["citations"] = []
            state["map_reduce_ok"] = True
            dp = dict(state.get("done_payload") or {})
            dp["map_reduce"] = True
            state["done_payload"] = dp
        else:
            state["map_reduce_ok"] = False
            state["precomputed_answer"] = ""
        return state

    async def _node_retrieval(self, state: ChatGraphState) -> ChatGraphState:
        q = state.get("redacted_message") or state.get("message") or ""
        active = list(state.get("active_source_ids") or [])
        include_g = _ncert_global_merge_allowed(state)

        print(f"[RETRIEVAL_NODE] include_ncert_global={state.get('include_ncert_global')} (raw from state)")
        print(f"[RETRIEVAL_NODE] ENABLE_NCERT_GLOBAL_IN_CHAT={getattr(settings, 'ENABLE_NCERT_GLOBAL_IN_CHAT', False)}")
        print(f"[RETRIEVAL_NODE] include_g={include_g} (effective merge flag)")
        print(f"[RETRIEVAL_NODE] active_source_ids={active}")
        
        if active:
            filter_dict: Optional[Dict[str, Any]] = {"source_id": {"$in": active}}
        elif include_g:
            # No user sources: avoid querying the whole tenant namespace; NCERT merge supplies chunks.
            filter_dict = {"source_id": {"$in": ["00000000-0000-0000-0000-000000000001"]}}
        else:
            filter_dict = None
        
        print(f"[RETRIEVAL_NODE] filter_dict={filter_dict}")
        print(f"[RETRIEVAL_NODE] Passing to retriever: include_ncert_global={include_g}")

        session_key = build_retrieval_session_key(
            chat_id=state.get("chat_id"),
            active_source_ids=active,
            include_ncert_global=include_g,
            ncert_class=state.get("ncert_class"),
            ncert_subject=state.get("ncert_subject"),
            ncert_chapter_no=state.get("ncert_chapter_no"),
        )
        state["retrieval_session_key"] = session_key
        try:
            prev = await self.retrieval_session_cache.get_chunks(session_key)
            if prev:
                self.retriever.previous_chunks = list(prev)
        except Exception as exc:
            print(f"[RETRIEVAL_SESSION_CACHE] load failed: {exc}")

        results = await self.retriever.retrieve(
            query=q,
            top_k=settings.TOP_K_CHUNKS,
            filter=filter_dict,
            conversation_history=state.get("effective_history") or state.get("history") or [],
            classified_intent=state.get("classified_intent") or None,
            classified_intent_confidence=state.get("intent_classification_confidence"),
            scope=state.get("scope") or None,
            requires_retrieval=state.get("requires_retrieval"),
            requires_attachment=state.get("requires_attachment"),
            include_ncert_global=include_g,
            ncert_class=state.get("ncert_class"),
            ncert_subject=state.get("ncert_subject"),
            ncert_chapter_no=state.get("ncert_chapter_no"),
            ncert_chapter_name=state.get("ncert_chapter_name"),
            ncert_concept=state.get("ncert_concept"),
        )

        state["matches"] = list(results.get("matches") or [])
        state["derived_hit"] = bool(results.get("derived_hit"))

        # Attach compact retrieval artifacts for admin trace explain view (no full prompt).
        try:
            from packages.core.monitoring.pipeline_trace import get_pipeline_trace_store, trace_snippet

            max_chunks = int(getattr(settings, "PIPELINE_TRACE_ARTIFACT_MAX_RETRIEVED_CHUNKS", 200))
            matches = list(state.get("matches") or [])[: max(0, max_chunks)]

            def _md(m: Dict[str, Any]) -> Dict[str, Any]:
                md = (m.get("metadata") or {}) if isinstance(m, dict) else {}
                text = str(md.get("text", "") or "")
                return {
                    "source_id": md.get("source_id"),
                    "source_type": md.get("source_type"),
                    "knowledge_namespace": md.get("knowledge_namespace"),
                    "page_number": md.get("page_number") or md.get("page_start"),
                    "text_preview": trace_snippet(text, 260) if text else "",
                }

            retrieved = []
            for m in matches:
                if not isinstance(m, dict):
                    continue
                cid = m.get("id")
                if not cid:
                    continue
                retrieved.append(
                    {
                        "chunk_id": cid,
                        "score": float(m.get("score", 0.0) or 0.0),
                        "metadata": _md(m),
                    }
                )

            store = get_pipeline_trace_store()
            store.set_artifact(
                "chat_request",
                {
                    "active_source_ids": active,
                    "include_ncert_global": bool(state.get("include_ncert_global")),
                    "include_ncert_global_effective": bool(include_g),
                    "ncert_class": state.get("ncert_class"),
                    "ncert_subject": state.get("ncert_subject"),
                    "ncert_chapter_no": state.get("ncert_chapter_no"),
                    "ncert_chapter_name": state.get("ncert_chapter_name"),
                    "tenant_namespace": str(self.tenant_id),
                    "ncert_global_namespace": getattr(settings, "NCERT_GLOBAL_PINECONE_NAMESPACE", "NcertDataGlobal"),
                    "filter_dict": filter_dict,
                },
            )
            store.set_artifact(
                "retrieval",
                {
                    "primary_query": state.get("primary_retrieval_query") or "",
                    "retrieved_chunks": retrieved,
                },
            )
        except Exception:
            pass

        rw = results.get("rewritten_queries")
        if isinstance(rw, list) and rw:
            state["rewritten_queries"] = [str(x).strip() for x in rw if str(x).strip()]
        else:
            state["rewritten_queries"] = [q]
        fq = results.get("focused_query")
        state["focused_query"] = (str(fq).strip() if fq else "") or q
        state["primary_retrieval_query"] = state["rewritten_queries"][0]
        state["rewritten_query"] = state["primary_retrieval_query"]
        try:
            to_store = list(self.retriever.previous_chunks or state.get("matches") or [])
            if to_store:
                await self.retrieval_session_cache.set_chunks(session_key, to_store)
        except Exception as exc:
            print(f"[RETRIEVAL_SESSION_CACHE] save failed: {exc}")
        return state

    def _max_chunk_chars_for_query(self, q: str) -> int:
        max_chars = int(getattr(settings, "MAX_CHUNK_LENGTH", 520))
        if _is_document_summary_query(q):
            max_chars = int(getattr(settings, "DOCUMENT_SUMMARY_MAX_CHUNK_CHARS", max_chars * 2))
        elif is_metadata_attribution_query(q):
            max_chars = int(getattr(settings, "METADATA_QUERY_MAX_CHUNK_CHARS", max_chars))
        return max_chars

    def _prepare_selected_matches(
        self,
        selected: List[Dict[str, Any]],
        q: str,
        titles: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        max_chars = self._max_chunk_chars_for_query(q)
        prepared: List[Dict[str, Any]] = []
        for m in selected:
            md = dict(m.get("metadata") or {})
            chunk_text = str(md.get("text", "") or "")
            if chunk_text and len(chunk_text) > max_chars:
                chunk_text = chunk_text[:max_chars]
                md["text"] = chunk_text
            source_id = md.get("source_id")
            metadata_title = md.get("display_source") or md.get("topic")
            source_title = (titles.get(source_id) if source_id else None) or metadata_title
            if source_title:
                md["display_source"] = source_title
            prepared.append({**m, "metadata": md})
        return prepared

    def _pack_context_from_matches(
        self, prepared: List[Dict[str, Any]]
    ) -> Tuple[str, List[Dict[str, Any]]]:
        from packages.core.rag.context_packer import pack_context_by_source

        return pack_context_by_source(prepared)

    async def _node_two_stage_grounding(self, state: ChatGraphState) -> ChatGraphState:
        from packages.core.rag.agents.two_stage_answering import (
            build_mini_context,
            should_use_mini_context,
        )

        selected = list(state.get("selected_matches") or state.get("matches") or [])
        q = state.get("rewritten_query") or state.get("message") or ""
        intent = state.get("classified_intent") or ""
        doc_summary = _is_document_summary_query_from_state(state)
        state["full_context_backup"] = state.get("context") or ""
        state["full_citations_backup"] = list(state.get("citations") or [])
        state["use_mini_context"] = False
        state["stage1_answer"] = ""
        state["needs_expansion"] = False

        if should_use_mini_context(
            intent=intent,
            query=q,
            match_count=len(selected),
            whole_file_summary=doc_summary,
            map_reduce_ok=bool(state.get("map_reduce_ok")),
        ):
            mini_ctx, mini_cites = build_mini_context(selected, n=2)
            state["use_mini_context"] = True
            state["context"] = mini_ctx
            state["citations"] = mini_cites
        return state

    async def _node_context_select(self, state: ChatGraphState) -> ChatGraphState:
        matches = state.get("matches") or []
        active = list(state.get("active_source_ids") or [])
        if active:
            matches = _filter_matches_to_active_sources(matches, active)
        q = state.get("rewritten_query") or state.get("message") or ""
        doc_summary = _is_document_summary_query_from_state(state)

        # If Phase-2 retrieval agents are enabled, they already selected a high-quality
        # set of chunks and enforced token budgets. Here we only need to format
        # numbered context + citations for the LLM.
        if settings.USE_RETRIEVAL_AGENTS:
            dedup_thr = float(getattr(settings, "CONTEXT_DEDUP_SIMILARITY_THRESHOLD", 0.82))
            selected = ContextDeduper(similarity_threshold=dedup_thr).dedupe_chunks(matches)
            if not selected and matches:
                selected = matches
            # Default cap for Q&A; whole-document summaries need many chunks (see Retriever + settings).
            cap = (
                getattr(settings, "DOCUMENT_SUMMARY_MAX_CONTEXT_CHUNKS", settings.MAX_CONTEXT_CHUNKS)
                if doc_summary
                else settings.MAX_CONTEXT_CHUNKS
            )
            if cap and len(selected) > cap:
                selected = selected[:cap]
            if getattr(settings, "ENABLE_SOURCE_INJECTION_SCAN", True):
                from packages.core.security.source_content_guard import filter_injection_matches

                selected, scan_meta = filter_injection_matches(selected, self.injection_detector)
                state["source_injection_scan"] = scan_meta
            state["selected_matches"] = selected

            source_ids = list(
                {(m.get("metadata", {}) or {}).get("source_id") for m in selected if (m.get("metadata", {}) or {}).get("source_id")}
            )
            titles = await self._load_source_titles([sid for sid in source_ids if sid])

            prepared = self._prepare_selected_matches(selected, q, titles)
            context, citations = self._pack_context_from_matches(prepared)
            state["citations"] = citations
            state["context"] = context

            # Attach compact selected-chunks artifact for trace explain view.
            try:
                from packages.core.monitoring.pipeline_trace import get_pipeline_trace_store, trace_snippet

                max_sel = int(getattr(settings, "PIPELINE_TRACE_ARTIFACT_MAX_SELECTED_CHUNKS", 120))
                selected_now = list(selected or [])[: max(0, max_sel)]
                selected_desc = []
                for m in selected_now:
                    if not isinstance(m, dict):
                        continue
                    md = m.get("metadata", {}) or {}
                    text = str(md.get("text", "") or "")
                    selected_desc.append(
                        {
                            "chunk_id": m.get("id"),
                            "score": float(m.get("score", 0.0) or 0.0),
                            "metadata": {
                                "source_id": md.get("source_id"),
                                "source_type": md.get("source_type"),
                                "knowledge_namespace": md.get("knowledge_namespace"),
                                "page_number": md.get("page_number") or md.get("page_start"),
                                "text_preview": trace_snippet(text, 260) if text else "",
                            },
                        }
                    )
                get_pipeline_trace_store().set_artifact(
                    "context_selector",
                    {
                        "selected_chunks": selected_desc,
                        "context_chars": len(state.get("context") or ""),
                        "final_context_sent_to_llm": trace_snippet(state.get("context") or "", 12000),
                    },
                )
            except Exception:
                pass
            return state

        # Deduplicate first
        dedup_thr = float(getattr(settings, "CONTEXT_DEDUP_SIMILARITY_THRESHOLD", 0.82))
        matches = ContextDeduper(similarity_threshold=dedup_thr).dedupe_chunks(matches)

        # Token-budget aware selection (existing agent)
        selected = self.context_selector.select_context(
            retrieved_chunks=matches,
            query=q,
            max_tokens=settings.CONTEXT_TOKEN_BUDGET,
            min_chunks=settings.MIN_CONTEXT_CHUNKS,
        )
        # Guardrail: if thresholding removes everything, fall back to top-N so we can emit citations
        # and provide grounded context when at least one match exists.
        if not selected and matches:
            selected = matches[: max(1, min(len(matches), settings.MIN_CONTEXT_CHUNKS or 1))]
        state["selected_matches"] = selected

        if getattr(settings, "ENABLE_SOURCE_INJECTION_SCAN", True):
            from packages.core.security.source_content_guard import filter_injection_matches

            selected, scan_meta = filter_injection_matches(selected, self.injection_detector)
            state["selected_matches"] = selected
            state["source_injection_scan"] = scan_meta

        # Source title lookup for citations/context grouping
        source_ids = list({(m.get("metadata", {}) or {}).get("source_id") for m in selected if (m.get("metadata", {}) or {}).get("source_id")})
        titles = await self._load_source_titles([sid for sid in source_ids if sid])

        prepared = self._prepare_selected_matches(selected, q, titles)
        context, citations = self._pack_context_from_matches(prepared)
        state["citations"] = citations
        state["context"] = context

        # Attach compact selected-chunks artifact for trace explain view.
        try:
            from packages.core.monitoring.pipeline_trace import get_pipeline_trace_store, trace_snippet

            max_sel = int(getattr(settings, "PIPELINE_TRACE_ARTIFACT_MAX_SELECTED_CHUNKS", 120))
            selected_now = list(selected or [])[: max(0, max_sel)]
            selected_desc = []
            for m in selected_now:
                if not isinstance(m, dict):
                    continue
                md = m.get("metadata", {}) or {}
                text = str(md.get("text", "") or "")
                selected_desc.append(
                    {
                        "chunk_id": m.get("id"),
                        "score": float(m.get("score", 0.0) or 0.0),
                        "metadata": {
                            "source_id": md.get("source_id"),
                            "source_type": md.get("source_type"),
                            "knowledge_namespace": md.get("knowledge_namespace"),
                            "page_number": md.get("page_number") or md.get("page_start"),
                            "text_preview": trace_snippet(text, 260) if text else "",
                        },
                    }
                )
            get_pipeline_trace_store().set_artifact(
                "context_selector",
                {
                    "selected_chunks": selected_desc,
                    "context_chars": len(state.get("context") or ""),
                    "final_context_sent_to_llm": trace_snippet(state.get("context") or "", 12000),
                },
            )
        except Exception:
            pass
        return state

    async def _node_context_grounding_gate(self, state: ChatGraphState) -> ChatGraphState:
        """
        Require packed context to be semantically and (by default) lexically related to the query
        before any answer LLM call. Prevents answers from model knowledge when chunks are weak/off-topic.
        """
        state["context_grounding_blocked"] = False
        state["context_grounding_passed"] = False
        state["context_grounding_eval_skipped"] = False
        state["context_grounding_max_cosine"] = 0.0
        state["context_grounding_reason"] = ""

        if not getattr(settings, "CHAT_STRICT_CONTEXT_GROUNDING", True):
            return state

        if self._tutor_ncert_scoped_with_chunks(state):
            state["context_grounding_passed"] = True
            state["context_grounding_eval_skipped"] = True
            state["context_grounding_reason"] = "tutor_ncert_scoped_chunks"
            return state

        q = (
            state.get("primary_retrieval_query")
            or state.get("rewritten_query")
            or state.get("redacted_message")
            or state.get("message")
            or ""
        ).strip()

        # Whole-doc synthesis uses many excerpts; lexical overlap with a short query is misleading.
        if _is_document_summary_query_from_state(state):
            state["context_grounding_eval_skipped"] = True
            state["context_grounding_passed"] = True
            state["context_grounding_reason"] = "document_summary_exempt"
            return state

        selected = state.get("selected_matches") or []
        chunk_texts = extract_chunk_texts_from_matches(selected)
        if not chunk_texts or not (state.get("context") or "").strip():
            return state

        use_lexical = not is_metadata_attribution_query(q)

        decision = await evaluate_context_grounding(
            embedder=self.embedder,
            query=q,
            selected_matches=selected,
            chunk_texts=chunk_texts,
            enable_lexical=use_lexical,
        )

        state["context_grounding_max_cosine"] = float(decision.max_cosine)
        state["context_grounding_reason"] = f"{decision.reason}:{decision.detail}"[:500]

        if decision.ok:
            state["context_grounding_passed"] = True
            return state

        state["context_grounding_blocked"] = True
        state["retrieval_relevance_passed"] = False
        state["generation_blocked_reason"] = "INSUFFICIENT_CONTEXT_SUPPORT"
        state["final_answer"] = "Not found in provided sources."
        state["citations"] = []
        state["context"] = ""
        state["selected_matches"] = []
        return state

    def _tutor_ncert_effective(self, state: ChatGraphState) -> bool:
        return bool(state.get("include_ncert_global")) and getattr(
            settings, "ENABLE_NCERT_GLOBAL_IN_CHAT", False
        )

    def _tutor_ncert_scoped_with_chunks(self, state: ChatGraphState) -> bool:
        """NCERT tutor notebooks lock class/subject/chapter; retrieved chunks are already scoped."""
        if not self._tutor_ncert_effective(state):
            return False
        if state.get("ncert_class") is None:
            return False
        if not str(state.get("ncert_subject") or "").strip():
            return False
        if state.get("ncert_chapter_no") is None and not str(state.get("ncert_chapter_name") or "").strip():
            return False
        selected = state.get("selected_matches") or state.get("matches") or []
        if selected:
            return True
        return bool(str(state.get("context") or "").strip())

    def _tutor_ncert_blocked_user_message(self, state: ChatGraphState) -> str:
        cls = state.get("ncert_class")
        subj_raw = (state.get("ncert_subject") or "").strip()
        subj_disp = subj_raw.replace("_", " ").title() if subj_raw else "Science"
        chapter_no = state.get("ncert_chapter_no")
        chapter_name = (state.get("ncert_chapter_name") or "").strip()
        chapter_bit = ""
        if chapter_no is not None and chapter_name:
            chapter_bit = f" (Chapter {chapter_no}: {chapter_name})"
        elif chapter_no is not None:
            chapter_bit = f" (Chapter {chapter_no})"
        elif chapter_name:
            chapter_bit = f" ({chapter_name})"
        if cls is not None:
            return (
                f"I could not find matching NCERT content for Class {cls} {subj_disp}"
                f"{chapter_bit} in the curriculum index. "
                "Try a different question, confirm the chapter selection, "
                "or upload a source PDF for this notebook and ask again."
            )
        return (
            "I could not find matching NCERT content for the selected class/chapter filters. "
            "Try a different question or upload a source PDF for this notebook."
        )

    async def _node_tutor_relevance_gate(self, state: ChatGraphState) -> ChatGraphState:
        state["tutor_generation_blocked"] = False
        state["generation_blocked_reason"] = ""
        state["retrieval_relevance_passed"] = True
        state["tutor_relevance_max_cosine"] = 0.0

        if not self._tutor_ncert_effective(state):
            return state

        if self._tutor_ncert_scoped_with_chunks(state):
            state["retrieval_relevance_passed"] = True
            return state

        if getattr(settings, "CHAT_STRICT_CONTEXT_GROUNDING", True) and state.get(
            "context_grounding_passed"
        ):
            state["tutor_relevance_max_cosine"] = float(state.get("context_grounding_max_cosine") or 0.0)
            state["retrieval_relevance_passed"] = True
            return state

        if not getattr(settings, "TUTOR_NCERT_RELEVANCE_GATE_ENABLED", True):
            state["retrieval_relevance_passed"] = True
            return state

        # Whole-chapter / document summaries are scoped by NCERT filters already; query–chunk
        # cosine is misleading for generic "summarize this chapter" prompts.
        if _is_document_summary_query_from_state(state):
            state["retrieval_relevance_passed"] = True
            return state

        selected = state.get("selected_matches") or state.get("matches") or []
        q = (
            state.get("primary_retrieval_query")
            or state.get("rewritten_query")
            or state.get("redacted_message")
            or state.get("message")
            or ""
        ).strip()

        chunk_texts: List[str] = []
        for m in selected:
            if not isinstance(m, dict):
                continue
            md = m.get("metadata") or {}
            if not isinstance(md, dict):
                md = {}
            t = (md.get("text") or "").strip()
            if t:
                chunk_texts.append(t)

        def _block(reason: str) -> None:
            state["retrieval_relevance_passed"] = False
            state["generation_blocked_reason"] = reason
            state["tutor_generation_blocked"] = True
            state["final_answer"] = self._tutor_ncert_blocked_user_message(state)
            state["citations"] = []
            state["context"] = ""
            state["selected_matches"] = []

        if not chunk_texts:
            packed = (state.get("context") or "").strip()
            if packed:
                chunk_texts = [packed]
            else:
                _block("NO_MATCHING_CHUNKS")
                return state

        max_sim, err = await max_relevance_vs_chunks(self.embedder, q, chunk_texts)
        state["tutor_relevance_max_cosine"] = float(max_sim)
        if err:
            _block("IRRELEVANT_CONTEXT")
            return state

        thresh = float(getattr(settings, "TUTOR_NCERT_MIN_CHUNK_RELEVANCE_COSINE", 0.34))
        if max_sim < thresh:
            _block("IRRELEVANT_CONTEXT")
            return state

        state["retrieval_relevance_passed"] = True
        return state

    def _source_relevance_gate_applies(self, state: ChatGraphState) -> bool:
        if self._tutor_ncert_effective(state):
            return False
        if not getattr(settings, "CHAT_SELECTED_SOURCES_RELEVANCE_GATE_ENABLED", True):
            return False
        return bool(state.get("active_source_ids"))

    def _chat_sources_blocked_user_message(self) -> str:
        return "Not found in the selected sources."

    async def _node_source_relevance_gate(self, state: ChatGraphState) -> ChatGraphState:
        state["source_relevance_blocked"] = False
        state["chat_global_fallback"] = False
        state["source_relevance_max_cosine"] = 0.0
        state["chat_selected_sources_max_retrieval_score"] = 0.0

        if not self._source_relevance_gate_applies(state):
            return state

        q_gate = (
            state.get("primary_retrieval_query")
            or state.get("rewritten_query")
            or state.get("redacted_message")
            or state.get("message")
            or ""
        ).strip()
        if _is_document_summary_query_from_state(state) and (
            state.get("selected_matches") or (state.get("context") or "").strip()
        ):
            state["retrieval_relevance_passed"] = True
            state["generation_blocked_reason"] = ""
            return state

        if getattr(settings, "CHAT_STRICT_CONTEXT_GROUNDING", True) and state.get(
            "context_grounding_passed"
        ):
            state["source_relevance_blocked"] = False
            state["chat_global_fallback"] = False
            state["retrieval_relevance_passed"] = True
            state["generation_blocked_reason"] = ""
            state["source_relevance_max_cosine"] = float(state.get("context_grounding_max_cosine") or 0.0)
            sm = state.get("selected_matches") or []
            scores = [float(m.get("score", 0.0) or 0.0) for m in sm if isinstance(m, dict)]
            state["chat_selected_sources_max_retrieval_score"] = float(max(scores) if scores else 0.0)
            return state

        state["retrieval_relevance_passed"] = True
        state["generation_blocked_reason"] = ""

        selected = state.get("selected_matches") or []
        q = (
            state.get("primary_retrieval_query")
            or state.get("rewritten_query")
            or state.get("redacted_message")
            or state.get("message")
            or ""
        ).strip()

        chunk_texts: List[str] = []
        scores: List[float] = []
        for m in selected:
            if not isinstance(m, dict):
                continue
            md = m.get("metadata") or {}
            if not isinstance(md, dict):
                md = {}
            t = (md.get("text") or "").strip()
            if t:
                chunk_texts.append(t)
                scores.append(float(m.get("score", 0.0) or 0.0))

        max_score = max(scores) if scores else 0.0
        state["chat_selected_sources_max_retrieval_score"] = float(max_score)

        def _block_hard(reason: str) -> None:
            state["retrieval_relevance_passed"] = False
            state["generation_blocked_reason"] = reason
            state["source_relevance_blocked"] = True
            state["final_answer"] = self._chat_sources_blocked_user_message()
            state["citations"] = []
            state["context"] = ""
            state["selected_matches"] = []

        def _use_global_fallback() -> bool:
            if not getattr(settings, "CHAT_ALLOW_GLOBAL_KNOWLEDGE_FALLBACK", False):
                return False
            state["chat_global_fallback"] = True
            state["retrieval_relevance_passed"] = False
            state["generation_blocked_reason"] = "GLOBAL_FALLBACK_USED"
            state["source_relevance_blocked"] = False
            state["citations"] = []
            state["context"] = ""
            state["selected_matches"] = []
            return True

        if not chunk_texts:
            if not _use_global_fallback():
                _block_hard("NO_MATCHING_CHUNKS")
            return state

        min_ret = float(getattr(settings, "CHAT_SELECTED_SOURCES_MIN_RETRIEVAL_SCORE", 0.30))
        if max_score < min_ret:
            if not _use_global_fallback():
                _block_hard("LOW_SIMILARITY")
            return state

        max_sim, err = await max_relevance_vs_chunks(self.embedder, q, chunk_texts)
        state["source_relevance_max_cosine"] = float(max_sim)
        if err:
            if not _use_global_fallback():
                _block_hard("IRRELEVANT_CONTEXT")
            return state

        cos_thresh = float(getattr(settings, "CHAT_SELECTED_SOURCES_MIN_CHUNK_RELEVANCE_COSINE", 0.34))
        if max_sim < cos_thresh:
            if not _use_global_fallback():
                _block_hard("IRRELEVANT_CONTEXT")
            return state

        state["retrieval_relevance_passed"] = True
        return state

    async def _node_generate(self, state: ChatGraphState) -> ChatGraphState:
        pre = (state.get("precomputed_answer") or "").strip()
        if pre:
            state["final_answer"] = _normalize_chat_tagged_response(pre)
            state["full_prompt"] = "[map-reduce]"
            return state

        if state.get("tutor_generation_blocked"):
            state.setdefault("final_answer", "")
            state["full_prompt"] = "[tutor-relevance-blocked]"
            return state

        if state.get("source_relevance_blocked"):
            state.setdefault("final_answer", "")
            state["full_prompt"] = "[source-relevance-blocked]"
            return state

        message = state.get("redacted_message") or state.get("message") or ""
        context = state.get("context") or ""
        document_summary = _is_document_summary_query_from_state(state)
        max_gen = (
            getattr(settings, "DOCUMENT_SUMMARY_CHAT_MAX_TOKENS", settings.CHAT_MAX_TOKENS)
            if document_summary
            else settings.CHAT_MAX_TOKENS
        )

        conv_hist = state.get("effective_history") or state.get("history") or []
        chat_rolling_summary, conversation_transcript = split_summary_and_transcript_for_prompt(
            conv_hist,
            max_messages=getattr(settings, "CHAT_PROMPT_MAX_HISTORY_MESSAGES", 16),
            max_chars_per_message=getattr(settings, "CHAT_PROMPT_MAX_CHARS_PER_MESSAGE", 900),
        )
        has_chat_summary = bool((chat_rolling_summary or "").strip())
        has_prior_conversation = bool(
            (conversation_transcript or "").strip() or has_chat_summary
        )

        primary_rq = state.get("primary_retrieval_query") or state.get("rewritten_query") or message
        focused_rq = state.get("focused_query") or message
        rw_list = state.get("rewritten_queries") or [message]
        retrieval_variants = rw_list[1:] if len(rw_list) > 1 else []
        intent_label = (state.get("classified_intent") or "").strip()
        chunk_n = len(
            state.get("selected_matches")
            or state.get("matches")
            or []
        )

        is_metadata_query = is_metadata_attribution_query(message)
        source_scope_meta = _is_source_scope_meta_from_state(state)
        tutor_strict_ncert_only = self._tutor_ncert_effective(state)
        chat_global_fallback = bool(state.get("chat_global_fallback"))
        try:
            from packages.core.knowledge.policy_loader import build_chat_policy_block

            chat_policy_block = build_chat_policy_block()
        except Exception:
            chat_policy_block = ""
        enrichment_block = ""
        if settings.IIL_ENABLED and self.db is not None:
            try:
                from packages.core.iil.enrichment import build_enrichment_block
                from packages.core.iil.concept_mapper import map_concept_from_query

                concept_id = await map_concept_from_query(self.db, message)
                enrichment_block = await build_enrichment_block(
                    self.db,
                    tenant_id=uuid.UUID(self.tenant_id),
                    concept_node_id=concept_id,
                )
            except Exception as exc:
                print(f"[IIL] enrichment skipped: {exc}")
        full_prompt = load_prompt(
            "chat/rag_prompt.j2",
            context=context,
            message=message,
            verbatim_user_message=message,
            llm_task_query=primary_rq,
            document_summary=document_summary,
            conversation_transcript=conversation_transcript,
            has_prior_conversation=has_prior_conversation,
            chat_rolling_summary=chat_rolling_summary,
            has_chat_summary=has_chat_summary,
            primary_retrieval_query=primary_rq,
            scope_focused_query=focused_rq,
            retrieval_query_variants=retrieval_variants,
            classified_intent=intent_label,
            context_chunk_count=chunk_n,
            is_metadata_query=is_metadata_query,
            source_scope_meta=source_scope_meta,
            tutor_strict_ncert_only=tutor_strict_ncert_only,
            chat_global_fallback=chat_global_fallback,
            chat_policy_block=chat_policy_block,
        )
        if enrichment_block:
            full_prompt = f"{full_prompt}\n\n{enrichment_block}"
        if getattr(settings, "ENABLE_PROMPT_INTEGRITY_CHECK", True):
            policy_injected = bool((chat_policy_block or "").strip())
            has_ctx = len((context or "").strip()) > 80
            ok_rag, reason_rag = validate_rag_compiled_prompt(
                full_prompt,
                has_substantive_context=has_ctx,
                tutor_strict_ncert_only=bool(tutor_strict_ncert_only),
                chat_global_fallback=bool(chat_global_fallback),
                policy_block_injected=policy_injected,
            )
            if not ok_rag:
                state["final_answer"] = self._prompt_injection_refusal_message()
                state["full_prompt"] = f"[prompt_integrity:{reason_rag}]"
                state["prompt_injection_detected"] = False
                state["injection_pattern_matched"] = f"compiled_prompt:{reason_rag}"
                state["generation_blocked_reason"] = "PROMPT_INTEGRITY"
                self._merge_guardrails_trace(state)
                return state
        state["full_prompt"] = full_prompt

        provider, model = get_model_for_task("chat")
        gen_temp = 0.35 if is_metadata_query else (0.45 if document_summary else 0.65)
        llm_client = get_llm_client(provider=provider, model=model, temperature=gen_temp)
        if self.tenant_id and getattr(settings, "ENABLE_BUDGET_ENFORCEMENT", False):
            from packages.core.guardrails.budget_enforcer import BudgetEnforcer

            await BudgetEnforcer().enforce_budget(str(self.tenant_id), estimated_cost=0.002)

        # Primary generation: stream tokens live to the SSE consumer as they arrive
        # (when running inside `stream()`) instead of buffering the full completion
        # first. Everything below this call — two-stage expansion, the not-found /
        # incomplete-answer / hallucination-guard retries, output formatting, and
        # moderation — is completely unchanged and still operates on `answer` as a
        # plain string. If any of that ends up changing the text after tokens were
        # already streamed, `stream()` detects the mismatch (comparing against what it
        # actually sent) and emits a `replace` event instead of silently diverging.
        if self._live_stream_queue is not None:
            streamed_parts: List[str] = []
            async for stream_chunk in llm_client.stream_generate(
                prompt=full_prompt,
                temperature=gen_temp,
                max_tokens=max_gen,
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                feature_tag="chat_langgraph",
            ):
                if stream_chunk.content:
                    streamed_parts.append(stream_chunk.content)
                    self._push_live(("token", stream_chunk.content))
            answer = "".join(streamed_parts).strip()
        else:
            resp = await llm_client.generate(
                prompt=full_prompt,
                temperature=gen_temp,
                max_tokens=max_gen,
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                feature_tag="chat_langgraph",
            )
            answer = (resp.content or "").strip()

        # Two-stage: expand to full context once when mini-context answer is insufficient.
        if state.get("use_mini_context") and not state.get("needs_expansion"):
            from packages.core.rag.agents.two_stage_answering import should_expand

            if should_expand(
                answer,
                context_grounding_blocked=bool(state.get("context_grounding_blocked")),
                citations=state.get("citations"),
            ):
                full_ctx = (state.get("full_context_backup") or "").strip()
                if full_ctx:
                    state["stage1_answer"] = answer
                    state["needs_expansion"] = True
                    context = full_ctx
                    state["context"] = context
                    state["citations"] = list(state.get("full_citations_backup") or [])
                    chunk_n = len(state.get("selected_matches") or state.get("matches") or [])
                    full_prompt = load_prompt(
                        "chat/rag_prompt.j2",
                        context=context,
                        message=message,
                        verbatim_user_message=message,
                        llm_task_query=primary_rq,
                        document_summary=document_summary,
                        conversation_transcript=conversation_transcript,
                        has_prior_conversation=has_prior_conversation,
                        chat_rolling_summary=chat_rolling_summary,
                        has_chat_summary=has_chat_summary,
                        primary_retrieval_query=primary_rq,
                        scope_focused_query=focused_rq,
                        retrieval_query_variants=retrieval_variants,
                        classified_intent=intent_label,
                        context_chunk_count=chunk_n,
                        is_metadata_query=is_metadata_query,
                        source_scope_meta=source_scope_meta,
                        tutor_strict_ncert_only=tutor_strict_ncert_only,
                        chat_global_fallback=chat_global_fallback,
                        chat_policy_block=chat_policy_block,
                    )
                    state["full_prompt"] = full_prompt
                    expand_resp = await llm_client.generate(
                        prompt=full_prompt,
                        temperature=gen_temp,
                        max_tokens=max_gen,
                        tenant_id=self.tenant_id,
                        user_id=self.user_id,
                        feature_tag="chat_langgraph_two_stage_expand",
                    )
                    answer = (expand_resp.content or "").strip()

        # Retry: if the model says "not found" but we *do* have citations/context,
        # it likely missed evidence. Re-prompt once with an explicit retry instruction.
        # Retry when the model says "not found" but retrieved context/citations exist.
        if (
            not chat_global_fallback
            and "not found in provided sources" in answer.lower()
            and context.strip()
            and (
                state.get("citations")
                or document_summary
                or source_scope_meta
                or _is_document_summary_query_from_state(state)
            )
        ):
            retry_prompt = (
                full_prompt
                + "\n\nRetry instruction: You previously replied with `Not found in provided sources.`, but "
                  f"{len(state.get('citations') or [])} context chunk(s) were supplied above. "
                  "Re-read **Context evidence** line by line. If **any** excerpt is relevant, you **must** answer from it "
                  "(paraphrase is fine). Only use `Not found in provided sources.` if **every** excerpt is clearly irrelevant."
            )
            if source_scope_meta:
                retry_prompt += (
                    "\n\nThis is a **source-scope** question: the user wants to know what their selected documents "
                    "are about. Summarize the subject/topic of each source from the excerpts. Do not refuse when "
                    "the excerpts contain chapter or topic content."
                )
            retry_resp = await llm_client.generate(
                prompt=retry_prompt,
                temperature=0.2,
                max_tokens=max_gen,
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                feature_tag="chat_langgraph_retry_not_found",
            )
            answer = (retry_resp.content or "").strip()

        # Retry: incomplete or truncated natural-language answer (common when context is marginal)
        if (
            not tutor_strict_ncert_only
            and not chat_global_fallback
            and _answer_looks_incomplete(answer)
            and context.strip()
            and "not found in provided sources" not in answer.lower()
        ):
            retry_prompt = (
                full_prompt
                + "\n\nCompletion instruction: Your previous answer was incomplete or ended mid-sentence. "
                  "Reply again with **complete sentences** that directly answer the user's question using only the context. "
                  "If the context does not support an answer, say exactly: `Not found in provided sources.`"
            )
            retry_resp = await llm_client.generate(
                prompt=retry_prompt,
                temperature=0.25,
                max_tokens=max_gen,
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                feature_tag="chat_langgraph_retry_incomplete",
            )
            answer = (retry_resp.content or "").strip()

        answer = _normalize_chat_tagged_response(answer)

        # Hallucination guard (deterministic) + conditional single retry (production-gated)
        # Not a multi-pass pipeline: only triggers on high-risk unsupported sentences.
        if getattr(settings, "ENABLE_HALLUCINATION_GUARD", False) and context.strip() and answer:
            try:
                from packages.core.rag.hallucination_guard import (
                    analyze_answer_support,
                    strict_retry_suffix,
                )

                hg = analyze_answer_support(
                    answer=answer,
                    context=context,
                    min_sentence_chars=int(getattr(settings, "HALLUCINATION_GUARD_MIN_SENTENCE_CHARS", 28)),
                    min_overlap_score=float(getattr(settings, "HALLUCINATION_GUARD_MIN_OVERLAP_SCORE", 0.22)),
                    enable_coarse_rescue=bool(
                        getattr(settings, "HALLUCINATION_GUARD_COARSE_RESCUE_ENABLED", True)
                    ),
                    coarse_recall_min=float(
                        getattr(settings, "HALLUCINATION_GUARD_COARSE_RECALL_MIN", 0.26)
                    ),
                )
                state["hallucination_guard"] = {
                    "supported_ratio": hg.supported_ratio,
                    "checked_sentences": hg.checked_sentences,
                    "unsupported_sentences_preview": hg.unsupported_sentences[:3],
                    "retried": False,
                }

                min_ratio = float(getattr(settings, "HALLUCINATION_GUARD_MIN_SUPPORTED_RATIO", 0.65))
                max_retry = int(getattr(settings, "HALLUCINATION_GUARD_MAX_RETRY", 1))
                if hg.checked_sentences > 0 and hg.supported_ratio < min_ratio and max_retry > 0:
                    retry_prompt = full_prompt + strict_retry_suffix(hg.unsupported_sentences)
                    retry_resp = await llm_client.generate(
                        prompt=retry_prompt,
                        temperature=0.25,
                        max_tokens=max_gen,
                        tenant_id=self.tenant_id,
                        user_id=self.user_id,
                        feature_tag="chat_langgraph_retry_hallucination_guard",
                    )
                    answer = _normalize_chat_tagged_response((retry_resp.content or "").strip())
                    state["hallucination_guard"]["retried"] = True

                # If we still appear unsupported after optional retry, refuse deterministically.
                # This prevents answers that look confident but are not grounded in the retrieved evidence.
                hg2 = analyze_answer_support(
                    answer=answer,
                    context=context,
                    min_sentence_chars=int(getattr(settings, "HALLUCINATION_GUARD_MIN_SENTENCE_CHARS", 28)),
                    min_overlap_score=float(getattr(settings, "HALLUCINATION_GUARD_MIN_OVERLAP_SCORE", 0.22)),
                    enable_coarse_rescue=bool(
                        getattr(settings, "HALLUCINATION_GUARD_COARSE_RESCUE_ENABLED", True)
                    ),
                    coarse_recall_min=float(
                        getattr(settings, "HALLUCINATION_GUARD_COARSE_RECALL_MIN", 0.26)
                    ),
                )
                state["hallucination_guard"]["supported_ratio_after"] = hg2.supported_ratio
                state["hallucination_guard"]["checked_sentences_after"] = hg2.checked_sentences
                # Do not overwrite a normal answer with "not found" based on brittle overlap — that caused
                # false refusals when chunks contained the answer but the model paraphrased.
                if (
                    getattr(settings, "HALLUCINATION_GUARD_FORCE_NOT_FOUND_ON_FAILURE", False)
                    and hg2.checked_sentences > 0
                    and hg2.supported_ratio < min_ratio
                    and "not found in provided sources" not in answer.lower()
                ):
                    answer = "Not found in provided sources."
            except Exception:
                pass

        # Post-generation processing (early stop, length limit, formatting, citation check)
        if getattr(settings, "USE_OUTPUT_OPTIMIZATION", True):
            if answer and settings.USE_EARLY_STOP and self.early_stop:
                stop_info = self.early_stop.should_stop(answer, message)
                if stop_info.get("should_stop"):
                    stop_at = self.early_stop.find_stop_point(answer)
                    if stop_at:
                        answer = answer[:stop_at].strip()
            if answer and self.length_limiter:
                limited = self.length_limiter.limit_output(answer)
                answer = limited.get("text", answer)
            if answer and self.formatter:
                try:
                    fmt = _output_format_for_intent(intent_label)
                    answer = self.formatter.format_response(
                        answer,
                        query=state.get("message") or "",
                        format_type=fmt,
                    )
                except Exception:
                    pass
            if answer and self.citation_enforcer:
                try:
                    _ = self.citation_enforcer.check_citations(answer, state.get("citations") or [])
                except Exception:
                    pass

        state["final_answer"] = answer
        return state

    def _node_moderation_output(self, state: ChatGraphState) -> ChatGraphState:
        answer = state.get("final_answer") or ""
        if not answer:
            state["final_output_text"] = answer
            return state

        try:
            res = check_moderation(answer)
            if moderation_indicates_block_output(res, answer):
                state["moderation_block_reason"] = "openai_moderation_output_block"
                state["final_output_text"] = self._moderation_refusal()
                return state
        except ValueError as e:
            msg = str(e).lower()
            if "not configured" in msg or "not installed" in msg:
                pass
            elif is_openai_moderation_configured() and not settings.MODERATION_FAIL_OPEN_ON_ERROR:
                state["moderation_block_reason"] = "openai_moderation_error_fail_closed"
                state["final_output_text"] = self._moderation_refusal()
                return state
        except Exception:
            if is_openai_moderation_configured() and not settings.MODERATION_FAIL_OPEN_ON_ERROR:
                state["moderation_block_reason"] = "openai_moderation_exception_fail_closed"
                state["final_output_text"] = self._moderation_refusal()
                return state

        # Safety filter (existing guardrail) + PII redaction (output)
        if settings.ENABLE_SAFETY_FILTERS:
            safe = self.safety_filter.check_output(answer, context="academic")
            if safe.get("blocked"):
                state["moderation_block_reason"] = "safety_filter_output_block"
                state["final_output_text"] = self._moderation_refusal()
                return state

        if settings.ENABLE_PII_DETECTION:
            redacted, _pii = self.pii_detector.redact(answer)
            answer = redacted

        state["final_output_text"] = answer
        return state

    def _node_eval(self, state: ChatGraphState) -> ChatGraphState:
        done: Dict[str, Any] = dict(state.get("done_payload") or {})
        done["prompt_injection_detected"] = bool(state.get("prompt_injection_detected", False))
        done["injection_pattern_matched"] = state.get("injection_pattern_matched")
        _gbr_early = (state.get("generation_blocked_reason") or "").strip()
        if _gbr_early:
            done["generation_blocked_reason"] = _gbr_early
        if state.get("trace_id"):
            done["trace_id"] = state["trace_id"]
        if state.get("use_cached_response"):
            done["cached"] = True
        if state.get("skip_rag"):
            done["skip_rag"] = True
            if state.get("dialog_route_reason"):
                done["dialog_route_reason"] = state["dialog_route_reason"]
        if self.confidence_scorer and state.get("final_output_text"):
            conf = self.confidence_scorer.calculate_confidence(
                query=state.get("message") or "",
                answer=state.get("final_output_text") or "",
                citations=state.get("citations") or [],
                retrieval_scores=[c.get("score", 0.0) for c in (state.get("citations") or [])],
                answer_length=len(state.get("final_output_text") or ""),
            )
            done["confidence_score"] = conf.get("confidence", 0.0)
            if conf.get("flagged"):
                done["low_confidence"] = True
        if state.get("hallucination_guard"):
            # Keep only small, non-sensitive summary fields in API payload.
            hg = dict(state.get("hallucination_guard") or {})
            done["hallucination_guard"] = {
                "supported_ratio": hg.get("supported_ratio"),
                "checked_sentences": hg.get("checked_sentences"),
                "retried": hg.get("retried", False),
            }
        if _gbr_early == "INSUFFICIENT_CONTEXT_SUPPORT":
            done["retrieval_relevance_passed"] = False
            done["answer_origin"] = "insufficient_context_support"
            done["selected_source_context_used"] = False
        elif _gbr_early == "INTENT_SECURITY_BLOCK":
            done["retrieval_relevance_passed"] = False
            done["answer_origin"] = "intent_security_block"
            done["selected_source_context_used"] = False
        elif self._tutor_ncert_effective(state):
            done["retrieval_relevance_passed"] = bool(state.get("retrieval_relevance_passed", True))
            reason = (state.get("generation_blocked_reason") or "").strip()
            if reason:
                done["generation_blocked_reason"] = reason
        elif state.get("chat_global_fallback"):
            done["retrieval_relevance_passed"] = False
            done["generation_blocked_reason"] = "GLOBAL_FALLBACK_USED"
            done["answer_origin"] = "global_only"
            done["selected_source_context_used"] = False
        elif self._source_relevance_gate_applies(state):
            done["retrieval_relevance_passed"] = bool(state.get("retrieval_relevance_passed", True))
            reason = (state.get("generation_blocked_reason") or "").strip()
            if reason:
                done["generation_blocked_reason"] = reason
            if bool(state.get("retrieval_relevance_passed", True)) and (
                state.get("final_output_text") or state.get("final_answer") or ""
            ).strip():
                done["answer_origin"] = "selected_sources"
                done["selected_source_context_used"] = True
        state["done_payload"] = done
        return state

    def _node_cache_store(self, state: ChatGraphState) -> ChatGraphState:
        """
        Persist successful assistant output so identical (query + sources) turns can hit CacheCheck.
        Previously only get() was wired; set() was never called, so the cache almost never worked.
        """
        if not self.answer_cache:
            return state
        if state.get("use_cached_response"):
            return state
        if state.get("tutor_generation_blocked"):
            return state
        if state.get("source_relevance_blocked"):
            return state
        if state.get("moderation_block_reason"):
            return state
        _gbr = (state.get("generation_blocked_reason") or "").strip()
        if _gbr in ("PROMPT_INTEGRITY", "INSUFFICIENT_CONTEXT_SUPPORT", "INTENT_SECURITY_BLOCK"):
            return state
        if (
            state.get("include_ncert_global")
            and getattr(settings, "ENABLE_NCERT_GLOBAL_IN_CHAT", False)
            and getattr(settings, "TUTOR_NCERT_BYPASS_ANSWER_CACHE", True)
        ):
            return state
        if (
            (state.get("active_source_ids") or [])
            and not (
                bool(state.get("include_ncert_global"))
                and getattr(settings, "ENABLE_NCERT_GLOBAL_IN_CHAT", False)
            )
            and getattr(settings, "CHAT_SELECTED_SOURCES_RELEVANCE_GATE_ENABLED", True)
            and getattr(settings, "CHAT_SELECTED_SOURCES_BYPASS_ANSWER_CACHE", True)
        ):
            return state
        out = (state.get("final_output_text") or "").strip()
        if not out:
            return state
        q = (state.get("redacted_message") or state.get("message") or "").strip()
        if not q:
            return state
        source_ids = list(state.get("active_source_ids") or [])
        citations = list(state.get("citations") or [])
        cache_extra = ""
        if state.get("include_ncert_global"):
            cache_extra = (
                f"ncert_v3|{state.get('ncert_class')}|{state.get('ncert_subject')}|"
                f"{state.get('ncert_chapter_no')}|{state.get('ncert_chapter_name')}"
            )
        try:
            self.answer_cache.set(
                q,
                source_ids,
                out,
                citations,
                tenant_id=self.tenant_id,
                cache_extra=cache_extra,
            )
        except Exception as e:
            print(f"[ANSWER_CACHE] Failed to store entry: {type(e).__name__}: {e}")
        return state

    async def stream(
        self,
        *,
        message: str,
        history: List[Dict[str, Any]],
        active_source_ids: List[str],
        include_ncert_global: bool = False,
        ncert_class: Optional[int] = None,
        ncert_subject: Optional[str] = None,
        ncert_chapter_no: Optional[int] = None,
        ncert_chapter_name: Optional[str] = None,
        ncert_concept: Optional[str] = None,
        force_whole_file_map_reduce: bool = False,
        chat_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Produce SSE events preserving the existing event/data shapes.

        The graph runs as a background task while this generator concurrently drains
        `self._live_stream_queue`: `_node_generate`'s primary answer call streams
        tokens onto that queue live (see `_node_generate`), so they reach the client as
        the LLM produces them instead of only after the whole graph (retrieval,
        grounding, generation, and any retries) has fully finished. Everything that can
        run after the primary call — two-stage expansion, retries, the hallucination
        guard, output formatting, output moderation — is unchanged and still decided
        from the fully-buffered `answer` string inside the graph; if any of it changes
        the final text after tokens were already streamed, a `replace` event is sent
        with the authoritative text (see the reconciliation below).
        """
        trace_id_opt: Optional[str] = None
        if getattr(settings, "ENABLE_PIPELINE_TRACE", True):
            trace_id_opt = str(uuid.uuid4())
            get_pipeline_trace_store().start_trace(trace_id_opt, self.tenant_id, self.user_id)

        subj = (ncert_subject or "").strip().lower() or None
        chapter_name = (ncert_chapter_name or "").strip() or None
        concept = (ncert_concept or "").strip() or None
        state: ChatGraphState = {
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "chat_id": chat_id,
            "message": message,
            "history": history,
            "active_source_ids": active_source_ids,
            "include_ncert_global": bool(include_ncert_global),
            "ncert_class": ncert_class,
            "ncert_subject": subj,
            "ncert_chapter_no": ncert_chapter_no,
            "ncert_chapter_name": chapter_name,
            "ncert_concept": concept,
            "trace_id": trace_id_opt or "",
            "force_whole_file_map_reduce": bool(force_whole_file_map_reduce),
        }

        live_queue: asyncio.Queue = asyncio.Queue()
        self._live_stream_queue = live_queue
        graph_task = asyncio.create_task(self._run_graph_and_signal(state, live_queue))

        streamed_text_parts: List[str] = []
        graph_result_state: Optional[ChatGraphState] = None
        graph_exc: Optional[BaseException] = None
        try:
            while True:
                kind, payload = await live_queue.get()
                if kind == "token":
                    streamed_text_parts.append(payload)
                    yield {"event": "chunk", "data": {"text": payload}}
                elif kind == "__graph_done__":
                    graph_result_state = payload
                    break
                elif kind == "__graph_error__":
                    graph_exc = payload
                    break
        finally:
            self._live_stream_queue = None
            if not graph_task.done():
                graph_task.cancel()

        if graph_exc is not None:
            if trace_id_opt:
                get_pipeline_trace_store().finalize_trace(trace_id_opt, success=False)
            from packages.core.guardrails.exceptions import BudgetExceededError

            if isinstance(graph_exc, BudgetExceededError):
                err_msg = str(graph_exc)
                # Budget enforcement runs before any token is produced, so in practice
                # nothing will have streamed yet; guard anyway so we never mix a partial
                # live answer with an unrelated buffered error message.
                if not streamed_text_parts:
                    for chunk in _split_stream_text(err_msg):
                        yield {"event": "chunk", "data": {"text": chunk}}
                yield {
                    "event": "done",
                    "data": {
                        "blocked": True,
                        "budget_exceeded": True,
                        "final_output_text": err_msg,
                        "error": err_msg,
                    },
                }
                return
            raise graph_exc

        state = graph_result_state if graph_result_state is not None else state
        if trace_id_opt:
            get_pipeline_trace_store().finalize_trace(trace_id_opt, success=True)
            print(
                f"[PIPELINE_TRACE] trace_id={trace_id_opt} "
                f"(browser console + /analytics/pipeline?trace_id={trace_id_opt})"
            )

        def _done_extra(base: Dict[str, Any]) -> Dict[str, Any]:
            if trace_id_opt:
                return {**base, "trace_id": trace_id_opt}
            return base

        # Blocked path: stream as normal assistant text so the UI shows an educational
        # refusal instead of an error toast / empty RAG "not found" behavior.
        if state.get("blocked") or state.get("error"):
            err_msg = (state.get("error") or "I'm not able to help with that.").strip()
            await self._record_guardrail_block_event(
                reason=(state.get("generation_blocked_reason") or state.get("error") or "guardrail_blocked_input")[
                    :200
                ],
                session_id=trace_id_opt,
            )
            for chunk in _split_stream_text(err_msg):
                yield {"event": "chunk", "data": {"text": chunk}}
            yield {
                "event": "done",
                "data": _done_extra(
                    {
                        "moderated": True,
                        "blocked": True,
                        "final_output_text": err_msg,
                        "prompt_injection_detected": bool(state.get("prompt_injection_detected", False)),
                        "injection_pattern_matched": state.get("injection_pattern_matched"),
                        "generation_blocked_reason": state.get("generation_blocked_reason"),
                    }
                ),
            }
            return

        # Cache-hit path
        if state.get("use_cached_response"):
            cached_answer = _normalize_chat_tagged_response(
                (state.get("cached_answer") or "").strip()
            )
            for c in state.get("cached_citations") or []:
                yield {"event": "citation", "data": c}
            for chunk in _split_stream_text(cached_answer):
                yield {"event": "chunk", "data": {"text": chunk}}
            yield {
                "event": "done",
                "data": _done_extra(
                    {
                        "cached": True,
                        "final_output_text": cached_answer,
                    }
                ),
            }
            return

        # Emit citations (restore from backup / matches if a gate cleared them post-retrieval).
        # Citations never depend on whether the primary answer was streamed live or
        # buffered, so this is unchanged and always computed from the final state.
        citations = list(state.get("citations") or [])
        blocked = bool(
            state.get("context_grounding_blocked")
            or state.get("source_relevance_blocked")
            or state.get("tutor_generation_blocked")
            or state.get("blocked")
        )
        if not citations and not blocked:
            citations = list(state.get("full_citations_backup") or [])
        if not citations and not blocked:
            selected = state.get("selected_matches") or state.get("matches") or []
            if selected:
                try:
                    q = state.get("rewritten_query") or state.get("message") or ""
                    titles = state.get("source_titles") or {}
                    prepared = self._prepare_selected_matches(selected, q, titles)
                    _, citations = self._pack_context_from_matches(prepared)
                except Exception:
                    citations = []
        for c in citations:
            yield {"event": "citation", "data": c}

        out_text = (state.get("final_output_text") or state.get("final_answer") or "").strip()
        streamed_text = "".join(streamed_text_parts).strip()

        if state.get("moderation_block_reason"):
            await self._record_guardrail_block_event(
                reason=str(state.get("moderation_block_reason")),
                session_id=trace_id_opt,
            )

        if streamed_text:
            # The primary answer already reached the client live, token by token. Only
            # send more text if something after the primary call — a retry, the
            # hallucination guard, output formatting/limiting, or output moderation —
            # produced a different final answer. We cannot un-send tokens already on
            # the wire, so tell the client to replace the displayed text outright
            # rather than silently leaving a stale/incorrect answer on screen.
            if out_text != streamed_text:
                yield {"event": "replace", "data": {"text": out_text}}
        else:
            # No live streaming happened for this turn (e.g. DirectChat conversational
            # reply, a tutor/source relevance gate block, or a whole-file map-reduce
            # precomputed answer never call the streaming primary-generation branch) —
            # unchanged buffered fake-stream behavior.
            for chunk in _split_stream_text(out_text):
                yield {"event": "chunk", "data": {"text": chunk}}

        done_data = dict(state.get("done_payload") or {})
        done_data["final_output_text"] = out_text
        if trace_id_opt:
            done_data["trace_id"] = trace_id_opt
        yield {"event": "done", "data": done_data}
