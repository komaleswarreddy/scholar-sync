from __future__ import annotations

from typing import Any, Dict, List, Optional

from packages.core.rag.vectorstores.pinecone_store import get_pinecone_index
from packages.core.rag.vectorstores.namespace import normalize_pinecone_namespace
from config.settings import settings
from packages.core.llm.openai_compat import build_openai_http_clients


class LlamaIndexRetrievalAdapter:
    """
    Retrieve chunks from Pinecone via LlamaIndex while returning the existing
    'matches' shape used throughout the codebase:

    {
      "matches": [
        {"id": "...", "score": 0.12, "metadata": {"text": "...", "source_id": "...", ...}},
        ...
      ]
    }
    """

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._namespace = normalize_pinecone_namespace(tenant_id)

    def _require_llamaindex(self):
        try:
            from llama_index.core import VectorStoreIndex  # noqa: F401
            from llama_index.vector_stores.pinecone import PineconeVectorStore  # noqa: F401
            from llama_index.core.vector_stores.types import MetadataFilters  # noqa: F401
        except Exception as e:  # pragma: no cover
            raise ValueError(
                "LlamaIndex dependencies not installed. "
                "Install llama-index-core and llama-index-vector-stores-pinecone."
            ) from e

    async def retrieve(
        self,
        *,
        query: str,
        top_k: int = 10,
        active_source_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        self._require_llamaindex()

        from llama_index.core import Settings as LISettings
        from llama_index.core import StorageContext, VectorStoreIndex
        from llama_index.vector_stores.pinecone import PineconeVectorStore
        from llama_index.embeddings.openai import OpenAIEmbedding

        pinecone_index = get_pinecone_index()
        vector_store = PineconeVectorStore(
            pinecone_index=pinecone_index,
            namespace=self._namespace,
        )

        # Match embedding model/dimensions used for ingestion and Pinecone index.
        sync_http_client, async_http_client = build_openai_http_clients()
        embed_kwargs: Dict[str, Any] = {
            "model": settings.OPENAI_EMBEDDING_MODEL,
            "dimensions": settings.OPENAI_EMBEDDING_DIMENSIONS,
        }
        if settings.OPENAI_API_KEY:
            embed_kwargs["api_key"] = settings.OPENAI_API_KEY
        if sync_http_client is not None:
            embed_kwargs["http_client"] = sync_http_client
        if async_http_client is not None:
            embed_kwargs["async_http_client"] = async_http_client
        LISettings.embed_model = OpenAIEmbedding(**embed_kwargs)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store, storage_context=storage_context
        )

        retriever_kwargs: Dict[str, Any] = {"similarity_top_k": top_k}

        # Metadata filtering by source_id matches your current Pinecone filter:
        # {"source_id": {"$in": active_source_ids}}
        if active_source_ids:
            try:
                from llama_index.core.vector_stores.types import (
                    MetadataFilter,
                    MetadataFilters,
                    FilterOperator,
                )

                retriever_kwargs["filters"] = MetadataFilters(
                    filters=[
                        MetadataFilter(
                            key="source_id",
                            operator=FilterOperator.IN,
                            value=active_source_ids,
                        )
                    ]
                )
            except Exception:
                # If filters API differs across LI versions, fall back to no filters
                # and rely on upstream restricting (not ideal, but avoids hard crash).
                pass

        retriever = index.as_retriever(**retriever_kwargs)
        nodes_with_scores = await retriever.aretrieve(query)

        matches: List[Dict[str, Any]] = []
        for item in nodes_with_scores:
            node = getattr(item, "node", None)
            score = float(getattr(item, "score", 0.0) or 0.0)
            if node is None:
                continue

            node_id = getattr(node, "node_id", None) or getattr(node, "id_", None)
            text = None
            try:
                text = node.get_content()
            except Exception:
                text = getattr(node, "text", None)

            metadata = dict(getattr(node, "metadata", {}) or {})

            # Ensure text is present in metadata for downstream compatibility.
            if text is not None and "text" not in metadata:
                metadata["text"] = text

            matches.append(
                {
                    "id": node_id,
                    "score": score,
                    "metadata": metadata,
                }
            )

        return {"matches": matches}
