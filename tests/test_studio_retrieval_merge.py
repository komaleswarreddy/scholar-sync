"""Unit tests for Studio multi-query retrieval merge (dedupe by vector id)."""

from packages.core.services.studio_service import merge_studio_match_lists


def test_merge_studio_match_lists_dedupes_by_id_keeps_best_score():
    m1 = [
        {"id": "a", "score": 0.5, "metadata": {"text": "low"}},
        {"id": "b", "score": 0.9, "metadata": {"text": "bbb"}},
    ]
    m2 = [
        {"id": "a", "score": 0.8, "metadata": {"text": "high"}},
        {"id": "c", "score": 0.7, "metadata": {"text": "ccc"}},
    ]
    ctx, n_included, n_unique = merge_studio_match_lists([m1, m2], max_chunks=10)
    assert "high" in ctx
    assert "low" not in ctx
    assert "bbb" in ctx
    assert "ccc" in ctx
    assert n_included == 3
    assert n_unique == 3


def test_merge_studio_match_lists_respects_max_chunks():
    matches = [
        {"id": f"id{i}", "score": float(i), "metadata": {"text": f"t{i}"}}
        for i in range(10)
    ]
    ctx, n_included, n_unique = merge_studio_match_lists([matches], max_chunks=3)
    assert n_unique == 10
    assert n_included == 3
    assert ctx.count("\n\n") == 2


def test_merge_studio_match_lists_balances_sources_for_mind_map():
    """Without balance, high-scoring source A would fill max_chunks; with balance, B appears too."""
    sid_a = "source-aaa"
    sid_b = "source-bbb"
    # Source A: many strong chunks; B: one weaker chunk
    m_a = [
        {
            "id": f"a{i}",
            "score": 1.0 - i * 0.01,
            "metadata": {"text": f"A{i}", "source_id": sid_a},
        }
        for i in range(20)
    ]
    m_b = [
        {
            "id": "b0",
            "score": 0.1,
            "metadata": {"text": "ONLY_B", "source_id": sid_b},
        }
    ]
    ctx_unbal, _, _ = merge_studio_match_lists([m_a + m_b], max_chunks=6)
    assert "ONLY_B" not in ctx_unbal

    ctx_bal, n_in, n_u = merge_studio_match_lists(
        [m_a + m_b],
        max_chunks=6,
        balance_source_ids=[sid_a, sid_b],
    )
    assert "ONLY_B" in ctx_bal
    assert n_in == 6
    assert n_u == 21
