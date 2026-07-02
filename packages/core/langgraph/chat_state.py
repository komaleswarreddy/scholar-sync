from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class ChatGraphState(TypedDict, total=False):
    # Input / identity
    tenant_id: str
    user_id: str
    chat_id: Optional[str]
    message: str
    history: List[Dict[str, Any]]
    active_source_ids: List[str]
    include_ncert_global: bool
    ncert_class: Optional[int]
    ncert_subject: Optional[str]
    ncert_chapter_no: Optional[int]
    ncert_chapter_name: Optional[str]
    ncert_concept: Optional[str]

    # Control flow
    blocked: bool
    error: str
    prompt_injection_detected: bool
    injection_pattern_matched: Optional[str]
    use_cached_response: bool
    cold_start: bool

    # Moderation / memory
    redacted_message: str
    effective_history: List[Dict[str, Any]]

    # Cache
    cached_answer: str
    cached_citations: List[Dict[str, Any]]

    # Dialog routing (skip RAG for pure small talk when ENABLE_DIALOG_ROUTER)
    skip_rag: bool
    dialog_route_reason: str

    # Intent / whole-document map-reduce
    classified_intent: str
    intent_classification_confidence: float
    # Retrieval scope hint from IntentClassifier: whole_document | section | fact | unspecified
    scope: str
    requires_retrieval: bool
    requires_attachment: bool
    whole_file_summary: bool
    map_reduce_ok: bool
    precomputed_answer: str
    # When true (API request): run map-reduce for exactly one active source regardless of dialog router / intent.
    force_whole_file_map_reduce: bool

    # Retrieval
    retrieval_session_key: str
    rewritten_query: str  # primary string used for embedding retrieval (best query first)
    focused_query: str  # scope-narrower output (when Phase 2 agents on)
    rewritten_queries: List[str]  # all variants used / merged in retrieval
    primary_retrieval_query: str  # same as rewritten_queries[0] when present
    matches: List[Dict[str, Any]]
    selected_matches: List[Dict[str, Any]]
    context: str
    citations: List[Dict[str, Any]]
    use_mini_context: bool
    stage1_answer: str
    needs_expansion: bool
    full_context_backup: str
    full_citations_backup: List[Dict[str, Any]]

    # Tutor / NCERT strict grounding (post-context-selector gate)
    tutor_generation_blocked: bool
    retrieval_relevance_passed: bool
    # e.g. NO_MATCHING_CHUNKS | LOW_SIMILARITY | IRRELEVANT_CONTEXT | GLOBAL_FALLBACK_USED
    generation_blocked_reason: Optional[str]
    tutor_relevance_max_cosine: float

    # Normal chat selected-sources relevance gate (after TutorRelevanceGate)
    source_relevance_blocked: bool
    source_relevance_max_cosine: float
    chat_selected_sources_max_retrieval_score: float
    chat_global_fallback: bool

    # Unified context support gate (post ContextSelector, pre Tutor/Source gates)
    context_grounding_blocked: bool
    context_grounding_passed: bool
    context_grounding_eval_skipped: bool
    context_grounding_max_cosine: float
    context_grounding_reason: str

    # Generation
    full_prompt: str
    final_answer: str
    final_output_text: str
    follow_ups: List[str]

    # Response quality signals (optional, for tracing / debugging)
    hallucination_guard: Dict[str, Any]

    # Done metadata
    done_payload: Dict[str, Any]

    # Debug: pipeline trace id (when ENABLE_PIPELINE_TRACE)
    trace_id: str
