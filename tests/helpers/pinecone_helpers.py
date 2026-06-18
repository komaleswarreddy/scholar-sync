"""Pinecone verification helpers for ingestion tests."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from config.settings import settings
from packages.core.rag.vectorstores.namespace import normalize_pinecone_namespace


def fetch_source_chunks(
    *,
    tenant_id: str,
    source_id: str,
    top_k: int = 100,
) -> List[Dict[str, Any]]:
    from pinecone import Pinecone

    if not settings.PINECONE_API_KEY or not settings.PINECONE_INDEX_NAME:
        raise RuntimeError("PINECONE_API_KEY and PINECONE_INDEX_NAME are required for live tests")

    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    index = pc.Index(settings.PINECONE_INDEX_NAME)
    namespace = normalize_pinecone_namespace(tenant_id)
    dummy = [0.0] * int(settings.OPENAI_EMBEDDING_DIMENSIONS)
    results = index.query(
        vector=dummy,
        top_k=top_k,
        include_metadata=True,
        namespace=namespace,
        filter={"source_id": source_id},
    )
    return list(results.get("matches", []))


def chunk_texts(chunks: List[Dict[str, Any]]) -> List[str]:
    texts: List[str] = []
    for match in chunks:
        metadata = match.get("metadata") or {}
        text = metadata.get("text") or ""
        if text:
            texts.append(text)
    return texts
