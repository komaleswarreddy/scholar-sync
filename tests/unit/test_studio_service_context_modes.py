"""StudioService context modes (selection_only, chat_hybrid) — retrieval boundaries."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from packages.core.services.studio_service import StudioService, compose_studio_hybrid_context


def test_compose_hybrid_includes_sections():
    out = compose_studio_hybrid_context("User: Q\nAssistant: A", "Source chunk one.")
    assert "## Conversation" in out
    assert "## Source excerpts" in out
    assert "User: Q" in out
    assert "Source chunk one" in out


@pytest.mark.asyncio
async def test_selection_only_skips_retrieval():
    svc = StudioService(db=MagicMock(), tenant_id="t1", user_id="u1")
    retrieve = AsyncMock()
    svc._retrieve_studio_context = retrieve
    gen_struct = AsyncMock(return_value={"task_type": "mind_map", "content": "# OK\n"})
    svc._generate_structured_task = gen_struct

    await svc.generate(
        "mind_map",
        [],
        custom_instructions=None,
        context_mode="selection_only",
        selection_text="a" * 20,
    )

    retrieve.assert_not_called()
    gen_struct.assert_awaited_once()
    ctx_passed = gen_struct.call_args[0][1]
    assert "a" * 20 in ctx_passed


@pytest.mark.asyncio
async def test_chat_hybrid_calls_retrieve_with_override():
    svc = StudioService(db=MagicMock(), tenant_id="t1", user_id="u1")

    async def fake_retrieve(sids, focus, task_type, *, max_chunks_override=None):
        assert max_chunks_override is not None
        return "SRC", {"queries_used": ["q1"], "chunk_count": 1}

    svc._retrieve_studio_context = fake_retrieve
    gen_mock = AsyncMock(return_value={"task_type": "mind_map", "content": "# H\n"})
    svc._generate_structured_task = gen_mock

    await svc.generate(
        "mind_map",
        ["id1"],
        context_mode="chat_hybrid",
        chat_transcript="User: test",
    )

    args = gen_mock.call_args[0]
    ctx = args[1]
    assert "User: test" in ctx
    assert "SRC" in ctx
