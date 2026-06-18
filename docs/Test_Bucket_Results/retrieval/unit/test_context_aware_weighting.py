"""Unit tests for post-rerank context-aware score adjustment."""

from packages.core.rag.context_aware_weighting import apply_context_aware_scores
from packages.core.rag.agents.intent_classifier import UserIntent


def test_apply_context_aware_scores_boosts_definition_match():
    matches = [
        {"id": "a", "score": 0.5, "metadata": {"chunk_type": "narrative", "concept_hint": ""}},
        {"id": "b", "score": 0.5, "metadata": {"chunk_type": "definition", "concept_hint": ""}},
    ]
    out = apply_context_aware_scores(
        matches,
        "What is the definition of photosynthesis?",
        max_boost=0.2,
        intent=UserIntent.DEFINITION,
    )
    assert out[0]["id"] == "b"
    assert out[0]["score"] > out[1]["score"]


def test_apply_context_aware_scores_hint_term_in_query():
    matches = [
        {"id": "x", "score": 0.9, "metadata": {"chunk_type": "", "concept_hint": "other"}},
        {"id": "y", "score": 0.9, "metadata": {"chunk_type": "", "concept_hint": "rank fusion, bm25"}},
    ]
    out = apply_context_aware_scores(matches, "Explain rank fusion", max_boost=0.2)
    assert out[0]["id"] == "y"


def test_apply_context_aware_scores_empty_input():
    assert apply_context_aware_scores([], "q", max_boost=0.15) == []
