"""Exploratory notebook chat: selected-source grounding and NCERT merge rules."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config.settings import settings
from packages.core.langgraph import chat_graph as cg
from packages.core.langgraph.chat_graph import (
    LangGraphChatPipeline,
    _filter_matches_to_active_sources,
    _is_document_summary_query,
    _is_document_summary_query_from_state,
    _ncert_global_merge_allowed,
    _query_strings_for_grounding,
)


def _state(**kwargs):
    base = {
        "message": "",
        "active_source_ids": [],
        "include_ncert_global": False,
    }
    base.update(kwargs)
    return base


def test_document_summary_detects_meta_source_query():
    assert _is_document_summary_query("what are those two sources about")


def test_document_summary_from_state_uses_original_message_after_rewrite():
    state = _state(
        message="Summarize the key points from these documents.",
        primary_retrieval_query="photosynthesis calvin cycle",
        rewritten_query="photosynthesis calvin cycle",
    )
    assert _is_document_summary_query_from_state(state) is True


def test_query_strings_for_grounding_dedupes():
    state = _state(
        message="hello",
        rewritten_query="hello",
        primary_retrieval_query="world",
    )
    qs = _query_strings_for_grounding(state)
    assert qs == ["hello", "world"]


def test_ncert_merge_blocked_when_uploads_selected_without_scope():
    state = _state(
        include_ncert_global=True,
        active_source_ids=["src-a", "src-b"],
        ncert_class=None,
    )
    with patch.object(settings, "ENABLE_NCERT_GLOBAL_IN_CHAT", True):
        assert _ncert_global_merge_allowed(state) is False


def test_ncert_merge_allowed_when_no_uploads():
    state = _state(include_ncert_global=True, active_source_ids=[])
    with patch.object(settings, "ENABLE_NCERT_GLOBAL_IN_CHAT", True):
        assert _ncert_global_merge_allowed(state) is True


def test_ncert_merge_allowed_when_tutor_scope_locked():
    state = _state(
        include_ncert_global=True,
        active_source_ids=["src-a"],
        ncert_class=12,
        ncert_subject="physics",
        ncert_chapter_no=5,
    )
    with patch.object(settings, "ENABLE_NCERT_GLOBAL_IN_CHAT", True):
        assert _ncert_global_merge_allowed(state) is True


def test_filter_matches_to_active_sources():
    matches = [
        {"metadata": {"source_id": "a", "text": "one"}},
        {"metadata": {"source_id": "b", "text": "two"}},
        {"metadata": {"source_id": "c", "text": "three"}},
    ]
    out = _filter_matches_to_active_sources(matches, ["a", "b"])
    assert len(out) == 2
    assert {m["metadata"]["source_id"] for m in out} == {"a", "b"}


@pytest.mark.asyncio
async def test_context_grounding_gate_passes_document_summary_even_if_rewrite_differs():
    pipeline = LangGraphChatPipeline(tenant_id="t1", user_id="u1", db=None)
    pipeline.embedder = MagicMock()

    state = _state(
        message="Summarize the key points from these documents.",
        primary_retrieval_query="unrelated rewritten query",
        selected_matches=[{"score": 0.5, "metadata": {"text": "Chapter on light reflection."}}],
        context="[1] Chapter on light reflection.",
    )

    with patch.object(settings, "CHAT_STRICT_CONTEXT_GROUNDING", True):
        out = await pipeline._node_context_grounding_gate(state)

    assert out["context_grounding_eval_skipped"] is True
    assert out["context_grounding_passed"] is True
    assert out.get("context_grounding_blocked") is False


@pytest.mark.asyncio
async def test_retrieval_node_disables_ncert_merge_for_selected_uploads():
    pipeline = LangGraphChatPipeline(tenant_id="t1", user_id="u1", db=None)
    pipeline.retriever = AsyncMock()
    pipeline.retriever.retrieve = AsyncMock(return_value={"matches": [], "rewritten_queries": ["q"]})
    pipeline.retrieval_session_cache = AsyncMock()
    pipeline.retrieval_session_cache.get_chunks = AsyncMock(return_value=None)
    pipeline.retrieval_session_cache.set_chunks = AsyncMock()

    state = _state(
        message="What is Ohm's law?",
        active_source_ids=["src-1", "src-2"],
        include_ncert_global=True,
        redacted_message="What is Ohm's law?",
    )

    with patch.object(settings, "ENABLE_NCERT_GLOBAL_IN_CHAT", True):
        await pipeline._node_retrieval(state)

    kwargs = pipeline.retriever.retrieve.await_args.kwargs
    assert kwargs["include_ncert_global"] is False


@pytest.mark.asyncio
async def test_context_select_filters_out_ncert_chunks_when_active_sources_set():
    pipeline = LangGraphChatPipeline(tenant_id="t1", user_id="u1", db=None)
    pipeline._load_source_titles = AsyncMock(return_value={})
    pipeline.injection_detector = MagicMock()

    state = _state(
        message="Summarize these documents",
        active_source_ids=["upload-a"],
        matches=[
            {"id": "1", "score": 0.9, "metadata": {"source_id": "upload-a", "text": "User PDF excerpt."}},
            {"id": "2", "score": 0.85, "metadata": {"source_id": "ncert-global", "text": "NCERT noise."}},
        ],
    )

    with patch.object(settings, "USE_RETRIEVAL_AGENTS", True):
        with patch.object(settings, "ENABLE_SOURCE_INJECTION_SCAN", False):
            out = await pipeline._node_context_select(state)

    selected = out.get("selected_matches") or []
    assert selected
    assert all((m.get("metadata") or {}).get("source_id") == "upload-a" for m in selected)


@pytest.mark.asyncio
async def test_two_stage_grounding_keeps_full_context_when_rewrite_drops_summary_words():
    pipeline = LangGraphChatPipeline(tenant_id="t1", user_id="u1", db=None)
    state = _state(
        message="Summarize the key points from these documents.",
        rewritten_query="coordinate geometry distance formula",
        classified_intent="question",
        selected_matches=[
            {"id": "1", "score": 0.9, "metadata": {"source_id": "a", "text": "chunk one " * 20}},
            {"id": "2", "score": 0.85, "metadata": {"source_id": "a", "text": "chunk two " * 20}},
            {"id": "3", "score": 0.8, "metadata": {"source_id": "b", "text": "chunk three " * 20}},
        ],
        context="[1] chunk one\n[2] chunk two\n[3] chunk three",
        citations=[{"index": 1}],
    )
    out = await pipeline._node_two_stage_grounding(state)
    assert out.get("use_mini_context") is False
    assert out.get("context") == state["context"]


def test_filter_matches_returns_empty_instead_of_ncert_fallback():
    matches = [
        {"metadata": {"source_id": "ncert-global", "text": "NCERT noise."}},
    ]
    out = _filter_matches_to_active_sources(matches, ["upload-a"])
    assert out == []
