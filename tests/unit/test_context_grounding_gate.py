"""Strict context grounding: lexical + decision wiring."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from config.settings import settings
from packages.core.rag.context_grounding_gate import (
    evaluate_context_grounding,
    lexical_gate_passes,
    significant_terms,
)


def test_significant_terms_xylem_query():
    t = significant_terms("Explain about xylem and phloem?", min_len=3)
    assert "xylem" in t
    assert "phloem" in t


def test_lexical_fails_wrong_chapter():
    terms = significant_terms("What is xylem and phloem?")
    chunks = [
        "Mitochondria are the powerhouse of the cell. The nucleus contains chromosomes.",
    ]
    ok, detail = lexical_gate_passes(
        terms,
        chunks,
        max_cosine=0.35,
        bypass_cosine=0.99,
    )
    assert ok is False
    assert "lexical_fail" in detail


def test_lexical_passes_when_terms_in_context():
    terms = significant_terms("What is photosynthesis?")
    chunks = ["Plants use photosynthesis to convert light into chemical energy."]
    ok, _ = lexical_gate_passes(terms, chunks, max_cosine=0.2, bypass_cosine=0.99)
    assert ok is True


@pytest.mark.asyncio
async def test_evaluate_passes_with_mocked_embeddings():
    from packages.core.rag import context_grounding_gate as cg

    async def fake_max_relevance(*_a, **_k):
        return (0.55, "")

    selected = [{"score": 0.45, "metadata": {"text": "Xylem transports water upward in plants."}}]
    texts = ["Xylem transports water upward in plants."]
    with patch.object(cg, "max_relevance_vs_chunks", new=fake_max_relevance):
        with patch.object(settings, "CONTEXT_GROUNDING_MIN_COSINE", 0.40):
            with patch.object(settings, "CONTEXT_GROUNDING_MIN_RETRIEVAL_SCORE", 0.28):
                d = await evaluate_context_grounding(
                    embedder=AsyncMock(),
                    query="explain xylem",
                    selected_matches=selected,
                    chunk_texts=texts,
                    enable_lexical=True,
                )
    assert d.ok is True
