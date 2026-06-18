"""Unit tests for tutor notebook prepare orchestration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from packages.core.services.tutor_notebook_prepare_service import (
    TutorNotebookPrepareService,
    _pick_auto_generate_types,
)


def test_pick_auto_generate_types_prefers_flagged():
    recs = [
        {"type": "flashcards", "auto_generate": True},
        {"type": "quiz", "auto_generate": False},
        {"type": "mind_map", "auto_generate": True},
        {"type": "slide_deck", "auto_generate": False},
    ]
    assert _pick_auto_generate_types(recs) == ["flashcards", "mind_map"]


def test_pick_auto_generate_types_uses_rank_order_when_unflagged():
    recs = [
        {"type": "mind_map", "auto_generate": False},
        {"type": "slide_deck", "auto_generate": False},
    ]
    assert _pick_auto_generate_types(recs) == ["mind_map", "slide_deck"]


def test_pick_auto_generate_types_fills_from_valid_types_when_sparse():
    recs = [{"type": "quiz", "auto_generate": False}]
    assert _pick_auto_generate_types(recs) == ["quiz", "flashcards"]


@pytest.mark.asyncio
async def test_prepare_uses_single_context_and_parallel_studio():
    db = MagicMock()
    tenant_id = "eeff7c1c-fe22-4573-ad93-a36f19ad4dc5"
    service = TutorNotebookPrepareService(db, tenant_id, "user-1")

    notebook = MagicMock()
    notebook.id = "63479326-f2c0-4974-bdae-bc078c042cbb"
    notebook.slug = "ch-3-money"
    notebook.settings = {}

    service.notebook_service.create_notebook = AsyncMock(return_value=notebook)
    service.bootstrap_service.fetch_scope_materials = AsyncMock(
        return_value=("ncert ctx", "topic sum", False)
    )
    service.bootstrap_service.generate_bootstrap_payload = AsyncMock(
        return_value={
            "opening_summary": "## Summary\n\nHello",
            "suggestions": [{"label": "A", "prompt": "p"}] * 3,
            "studio_recommendations": [
                {"type": "flashcards", "reason": "r", "auto_generate": True},
                {"type": "quiz", "reason": "r", "auto_generate": True},
                {"type": "mind_map", "reason": "r", "auto_generate": False},
                {"type": "slide_deck", "reason": "r", "auto_generate": False},
            ],
        }
    )
    service.bootstrap_service.fallback_payload = MagicMock()

    chat = MagicMock()
    chat.id = "chat-1"
    service.bootstrap_service.chat_service.create_chat = AsyncMock(return_value=chat)
    service.bootstrap_service.chat_service.add_message = AsyncMock()
    service.notebook_service.get_notebook = AsyncMock(return_value=notebook)
    service.notebook_service.update_notebook = AsyncMock()

    feature = MagicMock()
    feature.id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    service.feature_service.save_feature = AsyncMock(return_value=feature)

    generate_mock = AsyncMock(
        side_effect=[
            {"task_type": "flashcards", "data": [{"front": "a", "back": "b"}]},
            {"task_type": "quiz", "data": {"questions": []}},
        ]
    )
    service.studio_service.generate = generate_mock

    result = await service.prepare_notebook(
            title="Ch. 3",
            tutor_scope={
                "class_num": 10,
                "subject_key": "economics",
                "subject_slug": "economics",
                "chapter_no": 3,
                "chapter_title": "Money and Credit",
                "filter_chapter_name": "money and credit",
            },
        )

    assert result["assets_created"] == 2
    assert generate_mock.call_count == 2
    for call in generate_mock.call_args_list:
        kwargs = call.kwargs
        assert kwargs.get("context_mode") == "selection_only"
        assert kwargs.get("selection_text")

    assert service.bootstrap_service.fetch_scope_materials.call_count == 1
    assert "## Summary" in result["opening_summary"]
