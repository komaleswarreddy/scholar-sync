"""Unit tests for intent-gated retrieval strategy."""

from packages.core.rag.retrieval_strategy import resolve_retrieval_strategy, RetrievalStrategy
from packages.core.rag.agents.intent_classifier import UserIntent


def test_low_confidence_returns_neutral():
    s = resolve_retrieval_strategy(
        UserIntent.COMPARISON,
        intent_confidence=0.4,
        query="compare A and B",
        complexity_result={"word_count": 20},
        min_confidence=0.55,
    )
    assert s == RetrievalStrategy()


def test_comparison_high_confidence_widens_and_decomposes():
    s = resolve_retrieval_strategy(
        UserIntent.COMPARISON,
        intent_confidence=0.9,
        query="compare A and B",
        complexity_result={"word_count": 8},
        min_confidence=0.55,
    )
    assert s.initial_retrieval_k_multiplier == 4.0
    assert s.enable_query_decomposition_for_this_request is True


def test_definition_tightens_fetch():
    s = resolve_retrieval_strategy(
        UserIntent.DEFINITION,
        intent_confidence=0.95,
        query="define X",
        min_confidence=0.55,
    )
    assert s.initial_retrieval_k_multiplier == 2.5
    assert s.enable_query_decomposition_for_this_request is False


def test_explanation_decomposition_word_threshold():
    short = resolve_retrieval_strategy(
        UserIntent.EXPLANATION,
        intent_confidence=0.9,
        query="one two three four five",
        complexity_result={"word_count": 5},
        min_confidence=0.55,
        explanation_min_words_for_decomposition=12,
    )
    assert short.enable_query_decomposition_for_this_request is False

    long = resolve_retrieval_strategy(
        UserIntent.EXPLANATION,
        intent_confidence=0.9,
        query=" ".join([f"w{i}" for i in range(15)]),
        complexity_result={"word_count": 15},
        min_confidence=0.55,
        explanation_min_words_for_decomposition=12,
    )
    assert long.enable_query_decomposition_for_this_request is True
