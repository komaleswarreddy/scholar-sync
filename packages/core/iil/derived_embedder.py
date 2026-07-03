"""Embed derived knowledge artifacts into Pinecone derived namespace."""

from __future__ import annotations

import logging
import uuid
from typing import List, Optional

from config.settings import settings

logger = logging.getLogger(__name__)


def derived_namespace_for_tenant(tenant_id: str) -> str:
    suffix = settings.IIL_DERIVED_NAMESPACE_SUFFIX or "derived"
    return f"{tenant_id}-{suffix}"


async def embed_artifact(
    *,
    tenant_id: str,
    artifact_id: str,
    content: str,
    concept_node_id: Optional[str] = None,
    dimension_tags: Optional[List[str]] = None,
) -> Optional[str]:
    """Embed content and upsert to Pinecone; returns vector id."""
    if not settings.PINECONE_API_KEY or not content.strip():
        return None
    try:
        from packages.core.rag.embedder import Embedder

        embedder = Embedder(tenant_id)
        vector = await embedder.generate_embedding(content[:8000])
        if not vector:
            return None

        from pinecone import Pinecone

        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        index = pc.Index(settings.PINECONE_INDEX_NAME)
        ns = derived_namespace_for_tenant(tenant_id)
        vid = f"derived-{artifact_id}"

        metadata = {
            "artifact_id": artifact_id,
            "tenant_id": tenant_id,
            "source_type": "derived",
        }
        if concept_node_id:
            metadata["concept_node_id"] = concept_node_id
        if dimension_tags:
            metadata["dimension_tags"] = dimension_tags

        index.upsert(
            vectors=[{"id": vid, "values": vector, "metadata": metadata}],
            namespace=ns,
        )
        return vid
    except Exception as exc:
        logger.error("Derived embed failed for %s: %s", artifact_id, exc)
        return None


async def delete_artifact_embedding(tenant_id: str, embedding_id: str) -> None:
    if not settings.PINECONE_API_KEY or not embedding_id:
        return
    try:
        from pinecone import Pinecone

        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        index = pc.Index(settings.PINECONE_INDEX_NAME)
        ns = derived_namespace_for_tenant(tenant_id)
        index.delete(ids=[embedding_id], namespace=ns)
    except Exception as exc:
        logger.warning("Failed to delete derived embedding %s: %s", embedding_id, exc)
