from __future__ import annotations

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
)
from packages.core.security.openai_moderation import (
    is_openai_moderation_configured,
    moderation_indicates_block,
    moderation_indicates_block_output,
)
from packages.core.memory import AnswerCache, ChatSummarizer, MemoryManager
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
from packages.core.rag.metadata_query import is_metadata_attribution_query
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


def _normalize_chat_tagged_response(text: str) -> str:
    """
    Remove legacy <main_answer> / <follow_ups> XML-style wrappers from model output
    so the UI shows clean Markdown. Follow-ups become a normal ## section.
    """
    if not text or not text.strip():
        return (text or "").strip()
    t = text.strip()
    tl = t.lower()
    if "<main_answer>" not in tl and "<follow_ups>" not in tl:
        return t

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
        out = main_body
        if follow_body:
            fb = follow_body.strip()
            out = f"{out}\n\n---\n\n## Suggested questions\n\n{fb}"
        return out.strip()

    t = re.sub(r"</?main_answer>\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"</?follow_ups>\s*", "", t, flags=re.IGNORECASE)
    return t.strip()


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
    """Broad document/chapter summary requests need many chunks, not the default small cap."""
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
        )
    )

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
        g.add_edge("ContextSelector", "ContextGroundingGate")

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

    def _moderation_refusal(self) -> str:
        return self.refusals.get_refusal(RefusalReason.SAFETY_VIOLATION)

    def _prompt_injection_refusal_message(self) -> str:
        m = (getattr(settings, "PROMPT_INJECTION_REFUSAL_MESSAGE", "") or "").strip()
        return m or self.refusals.get_refusal(RefusalReason.PROMPT_INJECTION)

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
        if not self.db:
            return
        try:
            from sqlalchemy import select
            from packages.core.database.models.guardrail_user_block import GuardrailUserBlock
            from packages.core.database.models.alert_user_session import AlertUserSession

            tenant_uuid = uuid.UUID(self.tenant_id)
            session_uuid = None
            if session_id:
                try:
                    session_uuid = uuid.UUID(session_id)
                except Exception:
                    session_uuid = None

            # Upsert-ish block counter row per user in tenant
            existing = await self.db.execute(
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
                self.db.add(row)

            # Append alert session row for observability
            self.db.add(
                AlertUserSession(
                    tenant_id=tenant_uuid,
                    user_id=self.user_id,
                    session_id=session_uuid,
                    alert_type="guardrail_block",
                    alert_message=reason[:400],
                    severity="medium",
                )
            )
            await self.db.commit()
        except Exception:
            try:
                await self.db.rollback()
            except Exception:
                pass

    async def _load_source_titles(self, source_ids: List[str]) -> Dict[str, str]:
        """
        Best-effort lookup of source_id -> title from DB, matching existing chat behavior.
        If db not provided, returns empty mapping.
        """
        if not self.db or not source_ids:
            return {}
        try:
            import uuid as uuid_lib
            from sqlalchemy import select
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
            result = await self.db.execute(
                select(Source.id, Source.title).where(
                    Source.id.in_(source_uuids),
                    Source.tenant_id == tenant_uuid,
                    Source.user_id == self.user_id,
                )
            )
            title_map = {str(r.id): r.title for r in result.all() if r and r.title}

            unresolved = [sid for sid in source_uuids if str(sid) not in title_map]
            if unresolved:
                global_result = await self.db.execute(
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
                state["error"] = self.refusals.get_refusal(RefusalReason.PII_DETECTED)
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

        if settings.ENABLE_INTENT_GATE:
            intent = self.intent_gate.check_and_block(text)
            if intent.get("blocked"):
                state["blocked"] = True
                state["error"] = (
                    intent.get("message")
                    or self.refusals.get_refusal(RefusalReason.ACADEMIC_ONLY)
                )
                self._merge_guardrails_trace(state)
                return state

        if settings.ENABLE_SAFETY_FILTERS:
            safe = self.safety_filter.check_input(text, context="academic")
            if safe.get("blocked"):
                state["blocked"] = True
                state["error"] = self.refusals.get_refusal(RefusalReason.INAPPROPRIATE_CONTENT)
                self._merge_guardrails_trace(state)
                return state

        try:
            res = check_moderation(text)
            if moderation_indicates_block(res):
                state["blocked"] = True
                state["error"] = self.refusals.get_refusal(RefusalReason.INAPPROPRIATE_CONTENT)
                self._merge_guardrails_trace(state)
                return state
        except ValueError as e:
            msg = str(e).lower()
            if "not configured" in msg or "not installed" in msg:
                pass
            elif is_openai_moderation_configured() and not settings.MODERATION_FAIL_OPEN_ON_ERROR:
                state["blocked"] = True
                state["error"] = self.refusals.get_refusal(RefusalReason.GENERAL)
                self._merge_guardrails_trace(state)
                return state
        except Exception:
            if is_openai_moderation_configured() and not settings.MODERATION_FAIL_OPEN_ON_ERROR:
                state["blocked"] = True
                state["error"] = self.refusals.get_refusal(RefusalReason.GENERAL)
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

        full_prompt = load_prompt(
            "chat/direct_chat.j2",
            message=message,
            conversation_transcript=conversation_transcript,
            has_prior_conversation=has_prior_conversation,
            chat_rolling_summary=chat_rolling_summary,
            has_chat_summary=has_chat_summary,
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
        try:
            state["intent_classification_confidence"] = float(r.get("confidence", 0.5) or 0.5)
        except (TypeError, ValueError):
            state["intent_classification_confidence"] = 0.5
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
            state["citations"] = []
            state["selected_matches"] = []
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
        include_g = bool(state.get("include_ncert_global")) and getattr(
            settings, "ENABLE_NCERT_GLOBAL_IN_CHAT", False
        )
        
        # DEBUG: Log the checkbox state and active sources
        print(f"[RETRIEVAL_NODE] include_ncert_global={state.get('include_ncert_global')} (raw from state)")
        print(f"[RETRIEVAL_NODE] ENABLE_NCERT_GLOBAL_IN_CHAT={getattr(settings, 'ENABLE_NCERT_GLOBAL_IN_CHAT', False)}")
        print(f"[RETRIEVAL_NODE] include_g={include_g} (computed, after AND with setting)")
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
        
        results = await self.retriever.retrieve(
            query=q,
            top_k=settings.TOP_K_CHUNKS,
            filter=filter_dict,
            conversation_history=state.get("effective_history") or state.get("history") or [],
            classified_intent=state.get("classified_intent") or None,
            classified_intent_confidence=state.get("intent_classification_confidence"),
            include_ncert_global=include_g,
            ncert_class=state.get("ncert_class"),
            ncert_subject=state.get("ncert_subject"),
            ncert_chapter_no=state.get("ncert_chapter_no"),
            ncert_chapter_name=state.get("ncert_chapter_name"),
        )
        state["matches"] = results.get("matches", []) or []

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
        return state

    async def _node_context_select(self, state: ChatGraphState) -> ChatGraphState:
        matches = state.get("matches") or []
        q = state.get("rewritten_query") or state.get("message") or ""

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
                if _is_document_summary_query(q)
                else settings.MAX_CONTEXT_CHUNKS
            )
            if cap and len(selected) > cap:
                selected = selected[:cap]
            state["selected_matches"] = selected

            source_ids = list(
                {(m.get("metadata", {}) or {}).get("source_id") for m in selected if (m.get("metadata", {}) or {}).get("source_id")}
            )
            titles = await self._load_source_titles([sid for sid in source_ids if sid])

            citations: List[Dict[str, Any]] = []
            context_parts: List[str] = []
            for i, m in enumerate(selected, 1):
                md = m.get("metadata", {}) or {}
                chunk_text = md.get("text", "") or ""
                # Keep chunk context tight; the retriever may already have truncated,
                # but we re-check here to reduce noise.
                max_chars = getattr(settings, "MAX_CHUNK_LENGTH", 520)
                if _is_document_summary_query(q):
                    max_chars = getattr(settings, "DOCUMENT_SUMMARY_MAX_CHUNK_CHARS", max_chars * 2)
                elif is_metadata_attribution_query(q):
                    max_chars = getattr(settings, "METADATA_QUERY_MAX_CHUNK_CHARS", max_chars)
                if chunk_text and len(chunk_text) > max_chars:
                    chunk_text = chunk_text[:max_chars]

                source_id = md.get("source_id")
                metadata_title = md.get("display_source") or md.get("topic")
                source_title = (titles.get(source_id) if source_id else None) or metadata_title
                display_title = source_title or f"doc_{(source_id or 'unknown')[:8]}"
                page_num = md.get("page_start") or md.get("page_number")
                page_str = f"p{page_num}" if page_num else f"chunk{i}"

                context_parts.append(f"[{i}] {display_title} ({page_str}): {chunk_text}")

                citations.append(
                    {
                        "source_id": source_id,
                        "chunk_id": m.get("id"),
                        "text": md.get("text", "") or "",
                        "score": float(m.get("score", 0.0) or 0.0),
                        "source_title": source_title,
                        "page_number": page_num,
                    }
                )

            state["citations"] = citations
            state["context"] = "\n\n".join(context_parts)

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

        # Source title lookup for citations/context grouping
        source_ids = list({(m.get("metadata", {}) or {}).get("source_id") for m in selected if (m.get("metadata", {}) or {}).get("source_id")})
        titles = await self._load_source_titles([sid for sid in source_ids if sid])

        # Build numbered context items + citations.
        # Numbering ([1]..[N]) must match the order of `citations` so the model can cite properly.
        citations: List[Dict[str, Any]] = []
        context_parts: List[str] = []
        for i, m in enumerate(selected, 1):
            md = m.get("metadata", {}) or {}
            chunk_text = md.get("text", "") or ""
            source_id = md.get("source_id")
            metadata_title = md.get("display_source") or md.get("topic")
            source_title = (titles.get(source_id) if source_id else None) or metadata_title
            display_title = source_title or f"doc_{(source_id or 'unknown')[:8]}"
            page_num = md.get("page_start") or md.get("page_number")
            page_str = f"p{page_num}" if page_num else f"chunk{i}"

            context_parts.append(f"[{i}] {display_title} ({page_str}): {chunk_text}")

            citations.append(
                {
                    "source_id": source_id,
                    "chunk_id": m.get("id"),
                    "text": chunk_text,
                    "score": float(m.get("score", 0.0) or 0.0),
                    "source_title": source_title,
                    "page_number": page_num,
                }
            )

        state["citations"] = citations
        state["context"] = "\n\n".join(context_parts)

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

        q = (
            state.get("primary_retrieval_query")
            or state.get("rewritten_query")
            or state.get("redacted_message")
            or state.get("message")
            or ""
        ).strip()

        # Whole-doc synthesis uses many excerpts; lexical overlap with a short query is misleading.
        if _is_document_summary_query(q):
            state["context_grounding_eval_skipped"] = True
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

    def _tutor_ncert_blocked_user_message(self, state: ChatGraphState) -> str:
        cls = state.get("ncert_class")
        subj_raw = (state.get("ncert_subject") or "").strip()
        subj_disp = subj_raw.replace("_", " ").title() if subj_raw else "Science"
        if cls is not None:
            return (
                f"The requested information was not found in the selected NCERT Class {cls} "
                f"{subj_disp} chapters."
            )
        return (
            "The requested information was not found in the selected NCERT class/chapter filters."
        )

    async def _node_tutor_relevance_gate(self, state: ChatGraphState) -> ChatGraphState:
        state["tutor_generation_blocked"] = False
        state["generation_blocked_reason"] = ""
        state["retrieval_relevance_passed"] = True
        state["tutor_relevance_max_cosine"] = 0.0

        if not self._tutor_ncert_effective(state):
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

        selected = state.get("selected_matches") or []
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
        document_summary = _is_document_summary_query(message)
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
        tutor_strict_ncert_only = self._tutor_ncert_effective(state)
        chat_global_fallback = bool(state.get("chat_global_fallback"))
        try:
            from packages.core.knowledge.policy_loader import build_chat_policy_block

            chat_policy_block = build_chat_policy_block()
        except Exception:
            chat_policy_block = ""
        full_prompt = load_prompt(
            "chat/rag_prompt.j2",
            context=context,
            message=message,
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
            tutor_strict_ncert_only=tutor_strict_ncert_only,
            chat_global_fallback=chat_global_fallback,
            chat_policy_block=chat_policy_block,
        )
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
        resp = await llm_client.generate(
            prompt=full_prompt,
            temperature=gen_temp,
            max_tokens=max_gen,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            feature_tag="chat_langgraph",
        )
        answer = (resp.content or "").strip()

        # Retry: if the model says "not found" but we *do* have citations/context,
        # it likely missed evidence. Re-prompt once with an explicit retry instruction.
        if (
            not tutor_strict_ncert_only
            and not chat_global_fallback
            and "not found in provided sources" in answer.lower()
            and state.get("citations")
            and context.strip()
        ):
            retry_prompt = (
                full_prompt
                + "\n\nRetry instruction: You previously replied with `Not found in provided sources.`, but "
                  f"{len(state.get('citations') or [])} context chunk(s) were supplied above. "
                  "Re-read **Context evidence** line by line. If **any** excerpt is relevant, you **must** answer from it "
                  "(paraphrase is fine). Only use `Not found in provided sources.` if **every** excerpt is clearly irrelevant."
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

        # Post-generation processing (length limit, formatting, citation check)
        if answer and self.length_limiter:
            limited = self.length_limiter.limit_output(answer)
            answer = limited.get("text", answer)
        if answer and self.formatter:
            try:
                answer = self.formatter.format_response(answer, query=state.get("message") or "")
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
        if _gbr in ("PROMPT_INTEGRITY", "INSUFFICIENT_CONTEXT_SUPPORT"):
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
        force_whole_file_map_reduce: bool = False,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Produce SSE events preserving the existing event/data shapes.
        """
        trace_id_opt: Optional[str] = None
        if getattr(settings, "ENABLE_PIPELINE_TRACE", True):
            trace_id_opt = str(uuid.uuid4())
            get_pipeline_trace_store().start_trace(trace_id_opt, self.tenant_id, self.user_id)

        subj = (ncert_subject or "").strip().lower() or None
        chapter_name = (ncert_chapter_name or "").strip() or None
        state: ChatGraphState = {
            "db": self.db,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "message": message,
            "history": history,
            "active_source_ids": active_source_ids,
            "include_ncert_global": bool(include_ncert_global),
            "ncert_class": ncert_class,
            "ncert_subject": subj,
            "ncert_chapter_no": ncert_chapter_no,
            "ncert_chapter_name": chapter_name,
            "trace_id": trace_id_opt or "",
            "force_whole_file_map_reduce": bool(force_whole_file_map_reduce),
        }

        try:
            state = await self._graph.ainvoke(state)
        except Exception:
            if trace_id_opt:
                get_pipeline_trace_store().finalize_trace(trace_id_opt, success=False)
            raise
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

        # Emit citations first
        for c in state.get("citations") or []:
            yield {"event": "citation", "data": c}

        # Emit text chunks
        out_text = state.get("final_output_text") or ""
        if state.get("moderation_block_reason"):
            await self._record_guardrail_block_event(
                reason=str(state.get("moderation_block_reason")),
                session_id=trace_id_opt,
            )
        for chunk in _split_stream_text(out_text):
            yield {"event": "chunk", "data": {"text": chunk}}

        done_data = dict(state.get("done_payload") or {})
        done_data["final_output_text"] = out_text
        if trace_id_opt:
            done_data["trace_id"] = trace_id_opt
        yield {"event": "done", "data": done_data}
