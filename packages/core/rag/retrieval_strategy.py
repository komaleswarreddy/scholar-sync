"""
Intent- and complexity-gated retrieval parameters.

Uses the LangGraph intent label (no extra LLM call) to widen or narrow initial
fetch breadth and to gate optional query decomposition.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from packages.core.rag.agents.intent_classifier import UserIntent


@dataclass(frozen=True)
class RetrievalStrategy:
    """Per-request knobs derived from intent + confidence + query shape."""

    initial_retrieval_k_multiplier: float = 3.0
    enable_query_decomposition_for_this_request: bool = False
    skip_mmr: bool = False
    mmr_target_multiplier: float = 2.0


def resolve_retrieval_strategy(
    intent: UserIntent,
    intent_confidence: float,
    query: str,
    complexity_result: Optional[Dict[str, Any]] = None,
    *,
    min_confidence: float = 0.55,
    explanation_min_words_for_decomposition: int = 12,
) -> RetrievalStrategy:
    """
    Low-confidence intents yield a neutral strategy (legacy behavior).

    ``complexity_result`` may include ``word_count`` from QueryComplexityScorer;
    otherwise word count is derived from ``query``.
    """
    cr = complexity_result or {}
    wc = cr.get("word_count")
    if wc is None:
        wc = len(str(query or "").split())
    try:
        wc = int(wc)
    except (TypeError, ValueError):
        wc = 0

    conf = float(intent_confidence or 0.0)
    if conf < float(min_confidence):
        return RetrievalStrategy()

    # Broad retrieval for synthesizing or comparing across the corpus
    if intent in (UserIntent.COMPARISON, UserIntent.ANALYSIS):
        return RetrievalStrategy(
            initial_retrieval_k_multiplier=4.0,
            enable_query_decomposition_for_this_request=True,
            skip_mmr=False,
            mmr_target_multiplier=2.0,
        )

    if intent in (UserIntent.SUMMARY, UserIntent.WHOLE_DOCUMENT_SUMMARY):
        return RetrievalStrategy(
            initial_retrieval_k_multiplier=4.0,
            enable_query_decomposition_for_this_request=False,
            skip_mmr=False,
            mmr_target_multiplier=2.0,
        )

    if intent is UserIntent.DEFINITION:
        return RetrievalStrategy(
            initial_retrieval_k_multiplier=2.5,
            enable_query_decomposition_for_this_request=False,
            skip_mmr=False,
            mmr_target_multiplier=2.0,
        )

    if intent is UserIntent.EXPLANATION:
        decomp = wc >= int(explanation_min_words_for_decomposition)
        return RetrievalStrategy(
            initial_retrieval_k_multiplier=3.25,
            enable_query_decomposition_for_this_request=decomp,
            skip_mmr=False,
            mmr_target_multiplier=2.0,
        )

    if intent in (UserIntent.QUESTION, UserIntent.HOW_TO, UserIntent.CREATION):
        return RetrievalStrategy(
            initial_retrieval_k_multiplier=3.0,
            enable_query_decomposition_for_this_request=(intent is UserIntent.HOW_TO and wc >= 10),
            skip_mmr=False,
            mmr_target_multiplier=2.0,
        )

    # CONVERSATIONAL, GENERAL, and any future enum value
    return RetrievalStrategy()
