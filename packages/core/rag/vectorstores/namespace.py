"""
Pinecone namespace helper.

Pinecone namespaces are tenant-scoped. Use one canonical string everywhere:
upsert (PineconeVectorStore), LlamaIndex adapters, list/fetch (whole-file), and queries.
"""

from __future__ import annotations

import uuid


def normalize_pinecone_namespace(tenant_id: str) -> str:
    """
    Normalize tenant_id for use as Pinecone namespace.

    - Valid UUID strings -> canonical ``str(uuid.UUID(...))`` (stable casing/format).
    - Non-UUID (e.g. ``default``) -> returned unchanged.

    Namespace remains tenant-only; user isolation is via DB ``source_id`` + metadata filters.
    """
    if tenant_id is None:
        return "default"
    t = str(tenant_id).strip()
    if not t:
        return "default"
    try:
        return str(uuid.UUID(t))
    except (ValueError, TypeError, AttributeError):
        return t
