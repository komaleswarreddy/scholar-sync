from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class ChatGraphState(TypedDict, total=False):
    # Input / identity
    tenant_id: str
    user_id: str
    message: str
    history: List[Dict[str, Any]]
    active_source_ids: List[str]
    include_ncert_global: bool
    ncert_class: Optional[int]
    ncert_subject: Optional[str]

    # Control flow
    blocked: bool
    error: str
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
    whole_file_summary: bool
    map_reduce_ok: bool
    precomputed_answer: str

    # Retrieval
    rewritten_query: str  # primary string used for embedding retrieval (best query first)
    focused_query: str  # scope-narrower output (when Phase 2 agents on)
    rewritten_queries: List[str]  # all variants used / merged in retrieval
    primary_retrieval_query: str  # same as rewritten_queries[0] when present
    matches: List[Dict[str, Any]]
    selected_matches: List[Dict[str, Any]]
    context: str
    citations: List[Dict[str, Any]]

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

