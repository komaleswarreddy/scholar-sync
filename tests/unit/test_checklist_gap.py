"""Unit tests for checklist gap implementation (cache, session, retrieval, budget)."""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.core.guardrails.budget_enforcer import BudgetEnforcer
from packages.core.guardrails.cost_manager import CostManager
from packages.core.guardrails.exceptions import BudgetExceededError
from packages.core.memory.retrieval_session_cache import RetrievalSessionCache
from packages.core.processing.context_cache import ContextCache
from packages.core.rag.agents.context_deduper import ContextDeduper
from packages.core.rag.agents.query_complexity_scorer import QueryComplexityScorer
from packages.core.rag.agents.two_stage_answering import (
    build_mini_context,
    should_expand,
    should_use_mini_context,
)
from packages.core.rag.agents.intent_classifier import UserIntent
from packages.core.rag.context_packer import pack_context_by_source
from packages.core.rag.retriever import Retriever
from packages.core.orchestrator.task_router import TaskRouter


def _chunk(text: str, source_id: str = "s1", page: int = 1) -> dict:
    return {
        "id": f"{source_id}-{page}",
        "score": 0.9,
        "metadata": {
            "text": text,
            "source_id": source_id,
            "page_start": page,
            "display_source": f"Doc {source_id}",
        },
    }


def test_context_cache_round_trip():
    with tempfile.TemporaryDirectory() as tmp:
        cache = ContextCache(cache_dir=tmp)
        chunks = [("hello world", {"chunk_index": 0, "page_start": 1})]
        cache.cache_content(b"pdf-bytes", "hello world", chunks)
        hit = cache.get_cached_content(b"pdf-bytes", tenant_id="t1")
        assert hit is not None
        assert hit["text"] == "hello world"
        assert hit["chunks"] == chunks


def test_get_context_size_spec_values():
    with patch("packages.core.rag.retriever.PineconeVectorStore"), patch(
        "packages.core.rag.retriever.Embedder"
    ):
        r = Retriever(tenant_id="t1", user_id="u1")
    assert r.get_context_size(UserIntent.SUMMARY) == 3
    assert r.get_context_size(UserIntent.DEFINITION) == 5
    assert r.get_context_size(UserIntent.QUESTION) == 7
    assert r.get_context_size(UserIntent.EXPLANATION) == 10
    assert r.get_context_size(UserIntent.ANALYSIS) == 12


def test_query_complexity_skip_rewrite_simple():
    scorer = QueryComplexityScorer()
    result = scorer.score_complexity("what is photosynthesis")
    assert result.get("should_skip_rewrite") is True


def test_context_dedup_threshold_70():
    deduper = ContextDeduper(similarity_threshold=0.70)
    a = _chunk("The mitochondria is the powerhouse of the cell.")
    b = _chunk("The mitochondria is the powerhouse of the cell in biology.")
    out = deduper.dedupe_chunks([a, b])
    assert len(out) == 1


def test_pack_context_by_source_groups():
    matches = [
        _chunk("alpha", "src-a", 1),
        _chunk("beta", "src-a", 2),
        _chunk("gamma", "src-b", 3),
    ]
    ctx, cites = pack_context_by_source(matches)
    assert "## Source:" in ctx
    assert ctx.count("[1]") == 1
    assert ctx.count("[2]") == 1
    assert ctx.count("[3]") == 1
    assert len(cites) == 3


def test_two_stage_should_expand_on_not_found():
    assert should_expand("Not found in provided sources.", citations=[{"index": 1}]) is True
    assert should_expand("Photosynthesis converts light to energy.", citations=[{"index": 1}]) is False


def test_two_stage_mini_context_top_two():
    matches = [_chunk(f"t{i}") for i in range(5)]
    ctx, cites = build_mini_context(matches, n=2)
    assert len(cites) == 2
    assert "t0" in ctx and "t1" in ctx


def test_should_use_mini_context_short_question():
    assert should_use_mini_context(intent="question", query="what is DNA", match_count=4) is True
    assert should_use_mini_context(intent="summary", query="summarize chapter", match_count=4) is False


@pytest.mark.asyncio
async def test_retrieval_session_cache_memory_fallback():
    cache = RetrievalSessionCache(tenant_id="t1", user_id="u1")
    key = "sess-1"
    chunks = [_chunk("cached chunk")]
    await cache.set_chunks(key, chunks)
    loaded = await cache.get_chunks(key)
    assert len(loaded) == 1
    assert loaded[0]["metadata"]["text"] == "cached chunk"


def test_cost_manager_monthly_spend_filters():
    cm = CostManager()
    cm.metrics._llm_calls.clear()
    now = datetime.utcnow().isoformat()
    cm.metrics.record_llm_call(
        tenant_id="tenant-a",
        user_id="u1",
        model="gpt-4o-mini",
        provider="openai",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        cost=1.25,
        feature_tag="test",
    )
    cm.metrics._llm_calls[0]["timestamp"] = now
    assert cm.get_monthly_spend_usd("tenant-a") == 1.25
    assert cm.get_monthly_spend_usd("tenant-b") == 0.0


@pytest.mark.asyncio
async def test_budget_enforcer_blocks_over_cap():
    cm = CostManager()
    cm.metrics._llm_calls.clear()
    cm.metrics.record_llm_call(
        tenant_id="tenant-x",
        user_id="u1",
        model="gpt-4o-mini",
        provider="openai",
        prompt_tokens=1000,
        completion_tokens=500,
        total_tokens=1500,
        cost=150.0,
        feature_tag="test",
    )
    cm.metrics._llm_calls[0]["timestamp"] = datetime.utcnow().isoformat()
    enforcer = BudgetEnforcer()
    enforcer.cost_manager = cm
    with patch("packages.core.guardrails.budget_enforcer.settings") as mock_settings:
        mock_settings.ENABLE_BUDGET_ENFORCEMENT = True
        mock_settings.TENANT_MONTHLY_BUDGET_USD = 100.0
        mock_settings.BUDGET_ENFORCEMENT_GRACE_USD = 0.05
        with pytest.raises(BudgetExceededError):
            await enforcer.enforce_budget("tenant-x", estimated_cost=0.01)


def test_task_router_delegates_to_factory():
    routed = TaskRouter().route("chat")
    assert routed["task_type"] == "chat"
    assert routed["provider"] == "openai"
    assert routed["model"]
