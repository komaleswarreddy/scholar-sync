"""
Semantic relevance between user query and retrieved chunk text (Tutor / NCERT grounding gate).

Uses the same embedding model as tenant chat retrieval so query and chunk texts are comparable.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

from packages.core.rag.embedder import Embedder


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    sa = 0.0
    sb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        sa += x * x
        sb += y * y
    if sa <= 0.0 or sb <= 0.0:
        return 0.0
    return dot / (math.sqrt(sa) * math.sqrt(sb))


def max_query_chunk_cosine(
    query_vec: Sequence[float],
    chunk_vecs: Sequence[Sequence[float]],
) -> float:
    if not chunk_vecs:
        return 0.0
    return max(cosine_similarity(query_vec, cv) for cv in chunk_vecs)


async def max_relevance_vs_chunks(
    embedder: Embedder,
    query: str,
    chunk_texts: List[str],
    *,
    max_chars_per_chunk: int = 900,
    max_query_chars: int = 2000,
) -> Tuple[float, str]:
    """
    Embed query + chunk texts in one batch; return (max cosine sim, error or "").

    On empty chunk_texts returns (0.0, "").
    On embedding failure returns (0.0, error message).
    """
    q = (query or "").strip()
    if not q:
        return 0.0, ""
    q = q[:max_query_chars]
    texts: List[str] = [q]
    for t in chunk_texts:
        s = (t or "").strip()
        if s:
            texts.append(s[:max_chars_per_chunk])
    if len(texts) < 2:
        return 0.0, ""
    try:
        vecs = await embedder.batch_generate_embeddings(texts)
    except Exception as e:  # pragma: no cover - network/API
        return 0.0, str(e)[:200]
    if not vecs or len(vecs) != len(texts):
        return 0.0, "embedding_batch_mismatch"
    qv = vecs[0]
    chunk_vecs = vecs[1:]
    return max_query_chunk_cosine(qv, chunk_vecs), ""
