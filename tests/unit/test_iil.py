"""Unit tests for IIL enums and scoring."""

from packages.core.iil.curation_scorer import compute_score
from packages.core.iil.enums import SignalType, tier_allows_signal
from packages.core.rag.retriever import blend_retrieval_results


def test_blend_retrieval_results_weights():
    kb = [{"id": f"kb-{i}"} for i in range(10)]
    derived = [{"id": f"d-{i}"} for i in range(5)]
    merged = blend_retrieval_results(kb, derived)
    assert merged
    assert any(m["id"].startswith("d-") for m in merged)
    assert any(m["id"].startswith("kb-") for m in merged)


def test_tier_allows_signal_student():
    assert tier_allows_signal("student", SignalType.HELPFUL.value)
    assert not tier_allows_signal("student", SignalType.INACCURATE.value)
    assert not tier_allows_signal("student", SignalType.EXPERT_VALIDATED.value)


def test_tier_allows_signal_teacher():
    assert tier_allows_signal("teacher", SignalType.OFF_SYLLABUS.value)
    assert not tier_allows_signal("teacher", SignalType.EXPERT_NOTE.value)


def test_tier_allows_signal_sme():
    assert tier_allows_signal("sme", SignalType.EXPERT_NOTE.value)


def test_compute_score_expert_validated():
    class Log:
        user_tier = "sme"
        chain_depth = 4

    class Fb:
        signal_type = SignalType.EXPERT_VALIDATED.value
        user_tier = "sme"

    score, signals, reject = compute_score(Log(), [Fb()])
    assert not reject
    assert score >= 5
    assert signals.get("expert_validated")


def test_compute_score_inaccurate_hard_reject():
    class Fb:
        signal_type = SignalType.INACCURATE.value
        user_tier = "teacher"

    score, _, reject = compute_score(None, [Fb()])
    assert reject
    assert score <= -10
