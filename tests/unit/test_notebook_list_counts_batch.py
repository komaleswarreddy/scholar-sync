"""Unit tests for notebook list count batching."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from packages.core.services.notebook_service import NotebookService


@pytest.mark.asyncio
async def test_get_notebook_list_counts_batch_empty():
    db = AsyncMock()
    service = NotebookService(db, str(uuid4()), "user-1")
    assert await service.get_notebook_list_counts_batch([]) == {}


@pytest.mark.asyncio
async def test_get_notebook_list_counts_batch_returns_defaults():
    db = AsyncMock()
    nb_id = str(uuid4())
    mock_result = MagicMock()
    mock_result.all.return_value = []
    db.execute = AsyncMock(return_value=mock_result)

    service = NotebookService(db, str(uuid4()), "user-1")
    result = await service.get_notebook_list_counts_batch([nb_id])

    assert nb_id in result
    assert result[nb_id] == {
        "sources_count": 0,
        "notes_count": 0,
        "study_assets_count": 0,
        "quizzes_count": 0,
    }
