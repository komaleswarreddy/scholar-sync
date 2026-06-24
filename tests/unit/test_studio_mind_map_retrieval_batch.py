"""Studio mind map broad retrieval: batch embeddings + parallel Pinecone queries."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.core.services.studio_service import (
    STUDIO_BROAD_RETRIEVAL_QUERIES,
    StudioService,
    _studio_pinecone_query_sync,
)


@pytest.mark.asyncio
async def test_broad_retrieval_uses_batch_embeddings():
    svc = StudioService(db=MagicMock(), tenant_id="t1", user_id="u1")
    svc.vector_store = MagicMock()
    svc.vector_store.namespace = "tenant-ns"

    captured_batches: list[list[str]] = []

    async def fake_batch(texts):
        captured_batches.append(list(texts))
        return [[float(i)] * 16 for i, _ in enumerate(texts)]

    svc.vector_store.batch_generate_embeddings = AsyncMock(side_effect=fake_batch)

    async def immediate_to_thread(fn, *args, **kwargs):
        return fn(*args, **kwargs)

    with patch("packages.core.services.studio_service.asyncio.to_thread", side_effect=immediate_to_thread):
        with patch(
            "packages.core.services.studio_service._studio_pinecone_query_sync",
            return_value=[{"id": "v1", "score": 0.9, "metadata": {"text": "chunk"}}],
        ) as mock_sync:
            ctx, meta = await svc._retrieve_studio_context(
                ["source-1", "source-2"],
                retrieval_focus=None,
                task_type="mind_map",
            )

    assert len(captured_batches) == 1
    assert captured_batches[0] == list(STUDIO_BROAD_RETRIEVAL_QUERIES)
    assert mock_sync.call_count == len(STUDIO_BROAD_RETRIEVAL_QUERIES)
    assert meta["mode"] == "broad"
    assert meta["chunk_count"] >= 1
    assert "chunk" in ctx


@pytest.mark.asyncio
async def test_mind_map_multi_source_enables_balance_ids():
    """Case 02: 2+ sources + mind_map → balance_source_ids in merge path."""
    svc = StudioService(db=MagicMock(), tenant_id="t1", user_id="u1")
    svc.vector_store = MagicMock()
    svc.vector_store.namespace = "ns"

    svc.vector_store.batch_generate_embeddings = AsyncMock(
        return_value=[[0.1] * 8] * len(STUDIO_BROAD_RETRIEVAL_QUERIES)
    )

    async def immediate_to_thread(fn, *args, **kwargs):
        return fn(*args, **kwargs)

    merge_calls: list[dict] = []

    def capture_merge(per_query_matches, max_chunks, *, balance_source_ids=None):
        merge_calls.append({"balance": balance_source_ids, "max": max_chunks})
        return "merged", 2, 2

    with patch("packages.core.services.studio_service.asyncio.to_thread", side_effect=immediate_to_thread):
        with patch(
            "packages.core.services.studio_service._studio_pinecone_query_sync",
            return_value=[],
        ):
            with patch(
                "packages.core.services.studio_service.merge_studio_match_lists",
                side_effect=capture_merge,
            ):
                await svc._retrieve_studio_context(
                    ["s1", "s2"],
                    retrieval_focus=None,
                    task_type="mind_map",
                )

    assert merge_calls
    assert merge_calls[0]["balance"] == ["s1", "s2"]


def test_studio_pinecone_query_sync_returns_matches(monkeypatch):
    class FakeIndex:
        def query(self, **kwargs):
            assert kwargs["namespace"] == "test-ns"
            assert kwargs["top_k"] == 5
            return {"matches": [{"id": "m1", "score": 0.8, "metadata": {"text": "t"}}]}

    monkeypatch.setattr(
        "packages.core.services.studio_service.get_pinecone_index",
        lambda: FakeIndex(),
        raising=False,
    )
    # Patch import inside function
    import packages.core.rag.vectorstores.pinecone_store as ps

    monkeypatch.setattr(ps, "get_pinecone_index", lambda: FakeIndex())

    matches = _studio_pinecone_query_sync("test-ns", [0.1] * 8, 5, {"source_id": {"$in": ["a"]}})
    assert len(matches) == 1
    assert matches[0]["metadata"]["text"] == "t"
