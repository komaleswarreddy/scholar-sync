"""Integration-style tests for IIL flywheel components (no live LLM/Pinecone)."""

from packages.core.iil.curation_scorer import compute_score
from packages.core.iil.enums import SignalType, tier_allows_signal
from packages.core.rag.retriever import blend_retrieval_results
from packages.core.services.problem_solver_chat_bridge import _response_to_markdown


def test_flywheel_feedback_to_curation_score():
    """Expert validation on deep chain should produce high curation score."""

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


def test_flywheel_inaccurate_blocks_curation():
    class Fb:
        signal_type = SignalType.INACCURATE.value
        user_tier = "teacher"

    score, _, reject = compute_score(None, [Fb()])
    assert reject
    assert score <= -10


def test_flywheel_retrieval_blend_includes_derived():
    kb = [{"id": "kb-1", "score": 0.9}, {"id": "kb-2", "score": 0.8}]
    derived = [{"id": "derived-1", "score": 0.7}]
    merged = blend_retrieval_results(kb, derived)
    ids = {m["id"] for m in merged}
    assert "derived-1" in ids
    assert "kb-1" in ids


def test_flywheel_ps_response_markdown_for_message_persist():
    md = _response_to_markdown(
        {
            "title": "Approach",
            "sections": [{"heading": "Step 1", "bodyMarkdown": "Use F=ma"}],
            "finalAnswer": "42 m/s",
        }
    )
    assert "Approach" in md
    assert "F=ma" in md
    assert "42 m/s" in md


def test_flywheel_tier_gates_expert_note():
    assert tier_allows_signal("student", SignalType.HELPFUL.value)
    assert not tier_allows_signal("student", SignalType.EXPERT_NOTE.value)
    assert tier_allows_signal("sme", SignalType.EXPERT_NOTE.value)
