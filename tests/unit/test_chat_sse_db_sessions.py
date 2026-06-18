"""Verify chat pipeline DB access uses short-lived sessions, not request-scoped SSE holds."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.core.langgraph.chat_graph import LangGraphChatPipeline


@pytest.mark.asyncio
async def test_load_source_titles_opens_short_lived_session():
    """Each title lookup should acquire and release a session (not hold across LLM work)."""
    open_count = 0
    close_count = 0

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    class TrackingSession:
        async def __aenter__(self):
            nonlocal open_count
            open_count += 1
            return mock_session

        async def __aexit__(self, *args):
            nonlocal close_count
            close_count += 1

    pipeline = LangGraphChatPipeline(tenant_id="00000000-0000-0000-0000-000000000001", user_id="u1", db=None)

    with patch("packages.core.database.connection.db_session", return_value=TrackingSession()):
        await pipeline._load_source_titles(["00000000-0000-0000-0000-000000000002"])

    assert open_count == 1
    assert close_count == 1


@pytest.mark.asyncio
async def test_concurrent_title_lookups_each_get_own_session():
    """Concurrent lookups must not share one long-lived session."""
    peak_open = 0
    current_open = 0
    lock = asyncio.Lock()

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    class TrackingSession:
        async def __aenter__(self):
            nonlocal peak_open, current_open
            async with lock:
                current_open += 1
                peak_open = max(peak_open, current_open)
            await asyncio.sleep(0.02)
            return mock_session

        async def __aexit__(self, *args):
            nonlocal current_open
            async with lock:
                current_open -= 1

    pipeline = LangGraphChatPipeline(tenant_id="00000000-0000-0000-0000-000000000001", user_id="u1", db=None)

    with patch("packages.core.database.connection.db_session", return_value=TrackingSession()):
        await asyncio.gather(
            pipeline._load_source_titles(["00000000-0000-0000-0000-000000000002"]),
            pipeline._load_source_titles(["00000000-0000-0000-0000-000000000003"]),
            pipeline._load_source_titles(["00000000-0000-0000-0000-000000000004"]),
        )

    assert peak_open >= 2
