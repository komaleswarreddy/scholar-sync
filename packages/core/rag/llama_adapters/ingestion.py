from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from config.settings import settings
from packages.core.rag.vectorstores.pinecone_store import get_pinecone_index
from packages.core.rag.vectorstores.namespace import normalize_pinecone_namespace


@dataclass(frozen=True)
class LlamaIndexIngestionResult:
    nodes_indexed: int


class LlamaIndexIngestionAdapter:
    """
    Ingest text into Pinecone via LlamaIndex while preserving:
    - namespace == tenant_id
    - vector ids: {source_id}_chunk_{i}
    - metadata keys used by existing retrieval/synthesis
    """

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._namespace = normalize_pinecone_namespace(tenant_id)

    def _require_llamaindex(self):
        try:
            from llama_index.core import Settings as LISettings  # noqa: F401
            from llama_index.core.schema import TextNode  # noqa: F401
            from llama_index.core.node_parser import SentenceSplitter  # noqa: F401
            from llama_index.vector_stores.pinecone import PineconeVectorStore  # noqa: F401
            from llama_index.embeddings.openai import OpenAIEmbedding  # noqa: F401
        except Exception as e:  # pragma: no cover
            raise ValueError(
                "LlamaIndex dependencies not installed. "
                "Install llama-index-core, llama-index-vector-stores-pinecone, llama-index-embeddings-openai."
            ) from e

    def _build_nodes(
        self,
        *,
        text: str,
        source_id: str,
        pages: Optional[List[Tuple[int, str]]] = None,
    ) -> List["TextNode"]:
        """
        Build TextNodes with stable ids + metadata.

        We rely on LlamaIndex SentenceSplitter for chunking. We also add
        page metadata when available by aligning chunk text to page ranges
        using a best-effort heuristic.
        """
        from llama_index.core.node_parser import SentenceSplitter
        from llama_index.core.schema import TextNode

        chunk_size = getattr(settings, "CHUNK_SIZE", 1000)
        overlap_percent = getattr(settings, "CHUNK_OVERLAP_PERCENT", 0.12)
        chunk_overlap = int(chunk_size * overlap_percent)

        splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunks = splitter.split_text(text)

        # Best-effort page mapping: if we have pages, keep a running cursor in the full
        # concatenated text and assign pages based on where the chunk falls.
        page_spans: Optional[List[Tuple[int, int, int]]] = None
        if pages:
            spans: List[Tuple[int, int, int]] = []
            cursor = 0
            for page_num, page_text in pages:
                start = cursor
                cursor += len(page_text)
                end = cursor
                spans.append((page_num, start, end))
            page_spans = spans

        nodes: List[TextNode] = []
        cursor = 0
        for i, chunk_text in enumerate(chunks):
            node_id = f"{source_id}_chunk_{i}"

            metadata: Dict[str, Any] = {
                "source_id": source_id,
                "tenant_id": self._namespace,
                "chunk_index": i,
                # Important: existing pipeline expects text in metadata.
                "text": chunk_text,
            }

            if page_spans:
                # Find overlap between chunk position and page spans.
                start = cursor
                end = cursor + len(chunk_text)
                cursor = end

                covered_pages = [
                    page_num
                    for (page_num, p_start, p_end) in page_spans
                    if not (end <= p_start or start >= p_end)
                ]
                if covered_pages:
                    metadata["page_start"] = min(covered_pages)
                    metadata["page_end"] = max(covered_pages)
                    # Backward compatibility with existing citations code
                    metadata["page_number"] = metadata["page_start"]

            node = TextNode(text=chunk_text, id_=node_id, metadata=metadata)
            nodes.append(node)

        return nodes

    def _build_nodes_from_chunks(
        self,
        *,
        source_id: str,
        chunks_with_metadata: List[Tuple[str, Dict[str, Any]]],
    ) -> List["TextNode"]:
        """
        Build TextNodes from pre-chunked content (e.g. cache hit) while preserving
        vector id + metadata shape.
        """
        from llama_index.core.schema import TextNode

        nodes: List[TextNode] = []
        for i, (chunk_text, chunk_metadata) in enumerate(chunks_with_metadata):
            chunk_index = int(chunk_metadata.get("chunk_index", i))
            node_id = f"{source_id}_chunk_{chunk_index}"

            metadata: Dict[str, Any] = {
                "source_id": source_id,
                "tenant_id": self._namespace,
                "text": chunk_text,
                "chunk_index": chunk_index,
            }

            if "page_start" in chunk_metadata:
                metadata["page_start"] = chunk_metadata["page_start"]
                metadata["page_number"] = chunk_metadata["page_start"]
            if "page_end" in chunk_metadata:
                metadata["page_end"] = chunk_metadata["page_end"]

            nodes.append(TextNode(text=chunk_text, id_=node_id, metadata=metadata))

        # Keep deterministic ordering by chunk_index
        nodes.sort(key=lambda n: int(getattr(n, "metadata", {}).get("chunk_index", 0)))
        return nodes

    async def ingest_text(
        self,
        *,
        text: str,
        source_id: str,
        pages: Optional[List[Tuple[int, str]]] = None,
    ) -> LlamaIndexIngestionResult:
        self._require_llamaindex()

        from llama_index.core import Settings as LISettings
        from llama_index.core import StorageContext, VectorStoreIndex
        from llama_index.embeddings.openai import OpenAIEmbedding
        from llama_index.vector_stores.pinecone import PineconeVectorStore

        if not text or not text.strip():
            raise ValueError("Cannot ingest empty text")

        pinecone_index = get_pinecone_index()

        vector_store = PineconeVectorStore(
            pinecone_index=pinecone_index,
            namespace=self._namespace,
        )

        # Ensure embeddings match existing pipeline model and Pinecone index dimension.
        LISettings.embed_model = OpenAIEmbedding(
            model=settings.OPENAI_EMBEDDING_MODEL,
            dimensions=settings.OPENAI_EMBEDDING_DIMENSIONS,
        )

        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        nodes = self._build_nodes(text=text, source_id=source_id, pages=pages)

        # This will embed and write nodes to the vector store.
        VectorStoreIndex(nodes=nodes, storage_context=storage_context)

        return LlamaIndexIngestionResult(nodes_indexed=len(nodes))

    async def ingest_chunks(
        self,
        *,
        source_id: str,
        chunks_with_metadata: List[Tuple[str, Dict[str, Any]]],
    ) -> LlamaIndexIngestionResult:
        """
        Ingest already-chunked text into Pinecone using LlamaIndex embedding + write.
        Used when the pipeline hits ContextCache and we want to avoid re-splitting.
        """
        self._require_llamaindex()

        from llama_index.core import Settings as LISettings
        from llama_index.core import StorageContext, VectorStoreIndex
        from llama_index.embeddings.openai import OpenAIEmbedding
        from llama_index.vector_stores.pinecone import PineconeVectorStore

        if not chunks_with_metadata:
            raise ValueError("Cannot ingest empty chunks")

        pinecone_index = get_pinecone_index()
        vector_store = PineconeVectorStore(
            pinecone_index=pinecone_index,
            namespace=self._namespace,
        )

        LISettings.embed_model = OpenAIEmbedding(
            model=settings.OPENAI_EMBEDDING_MODEL,
            dimensions=settings.OPENAI_EMBEDDING_DIMENSIONS,
        )
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        nodes = self._build_nodes_from_chunks(
            source_id=source_id, chunks_with_metadata=chunks_with_metadata
        )

        VectorStoreIndex(nodes=nodes, storage_context=storage_context)
        return LlamaIndexIngestionResult(nodes_indexed=len(nodes))

