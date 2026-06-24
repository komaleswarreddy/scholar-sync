"""
Mind map NotebookLM source-only grounding — unit test matrix.

Covers Cases 01–05 from notebooklm-vs-scholarsync-mindmap.html plus regression
guards for other Studio task types (quiz chat_hybrid, slide_deck selection_only).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from apps.api.schemas.studio import StudioRequest
from packages.core.services.studio_service import (
    STUDIO_BROAD_RETRIEVAL_QUERIES,
    StudioService,
)


def _mind_map_svc() -> StudioService:
    return StudioService(db=MagicMock(), tenant_id="t1", user_id="u1")


@pytest.mark.parametrize(
    "context_mode,chat_transcript,selection_text",
    [
        ("sources_only", None, None),
        ("chat_hybrid", "User: short question\nAssistant: brief answer", None),
        (
            "chat_hybrid",
            "User: " + ("long chat line. " * 500),
            None,
        ),
        ("selection_only", None, "highlighted excerpt text" * 2),
    ],
    ids=[
        "case01_no_chat",
        "case03_minimal_chat",
        "case04_rich_chat",
        "case05_selection_override",
    ],
)
@pytest.mark.asyncio
async def test_mind_map_always_sources_only_context(context_mode, chat_transcript, selection_text):
    """Cases 01, 03, 04, 05: mind_map never uses chat or selection as primary context."""
    svc = _mind_map_svc()
    retrieve = AsyncMock(return_value=("SOURCE_CTX", {"queries_used": ["broad"], "chunk_count": 5}))
    svc._retrieve_studio_context = retrieve
    gen = AsyncMock(return_value={"task_type": "mind_map", "content": "# Hub\n## A\n"})
    svc._generate_structured_task = gen

    await svc.generate(
        "mind_map",
        ["src-a", "src-b"],
        context_mode=context_mode,
        chat_transcript=chat_transcript,
        selection_text=selection_text,
    )

    retrieve.assert_awaited_once()
    assert retrieve.call_args.kwargs.get("max_chunks_override") is None
    ctx = gen.call_args[0][1]
    assert ctx == "SOURCE_CTX"
    assert "## Conversation" not in ctx
    if chat_transcript:
        assert chat_transcript[:40] not in ctx
    if selection_text:
        assert selection_text not in ctx


def test_case05_empty_sources_sources_only_validation():
    """Mind map with no sources fails at API schema (same as other Studio tasks)."""
    with pytest.raises(ValidationError):
        StudioRequest(task_type="mind_map", source_ids=[], context_mode="sources_only")


def test_case05_selection_only_schema_still_valid_but_service_overrides():
    """API accepts selection_only for mind_map; service forces retrieval (see async test)."""
    req = StudioRequest(
        task_type="mind_map",
        source_ids=["ignored-by-selection-mode"],
        context_mode="selection_only",
        selection_text="x" * 20,
    )
    assert req.context_mode == "selection_only"
    assert req.source_ids == []


@pytest.mark.asyncio
async def test_case02_multi_source_passes_selected_source_count():
    """Multi-source: eff_source_count passed to generator for prompt synthesis rules."""
    svc = _mind_map_svc()
    svc._retrieve_studio_context = AsyncMock(
        return_value=("CTX", {"queries_used": list(STUDIO_BROAD_RETRIEVAL_QUERIES[:2]), "chunk_count": 10})
    )
    gen = AsyncMock(return_value={"task_type": "mind_map", "content": "# Hub\n"})
    svc._generate_structured_task = gen

    await svc.generate("mind_map", ["s1", "s2"])

    assert gen.call_args.kwargs.get("selected_source_count") == 2


@pytest.mark.asyncio
async def test_regression_quiz_still_uses_chat_hybrid():
    """Quiz must still honor chat_hybrid (mind_map-only override must not leak)."""
    svc = _mind_map_svc()

    async def fake_retrieve(sids, focus, task_type, *, max_chunks_override=None, **kwargs):
        assert max_chunks_override is not None
        return "SRC", {"queries_used": ["q"], "chunk_count": 1}

    svc._retrieve_studio_context = fake_retrieve
    gen = AsyncMock(return_value={"task_type": "quiz", "data": {"questions": []}})
    svc._generate_structured_task = gen

    await svc.generate(
        "quiz",
        ["id1"],
        context_mode="chat_hybrid",
        chat_transcript="User: focus on chapter 3",
    )

    ctx = gen.call_args[0][1]
    assert "User: focus on chapter 3" in ctx
    assert "SRC" in ctx


@pytest.mark.asyncio
async def test_regression_slide_deck_selection_only_skips_retrieval():
    """Slide deck selection_only must still skip retrieval (mind_map override is task-specific)."""
    svc = _mind_map_svc()
    retrieve = AsyncMock()
    svc._retrieve_studio_context = retrieve
    gen = AsyncMock(return_value={"task_type": "slide_deck", "content": "# Slide 1\n"})
    svc._generate_structured_task = gen
    excerpt = "selected paragraph from chat" * 2

    await svc.generate(
        "slide_deck",
        [],
        context_mode="selection_only",
        selection_text=excerpt,
    )

    retrieve.assert_not_called()
    assert excerpt in gen.call_args[0][1]
