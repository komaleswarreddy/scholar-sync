"""
Vector Store Facade

Facade pattern that delegates to specific vector store implementations.
Currently uses Pinecone, but can be extended to support multiple providers.
"""

from typing import List, Dict, Any, Optional
from packages.core.rag.vectorstores.pinecone_store import PineconeVectorStore


class VectorStore:
    """
    Facade for vector store operations.
    
    Delegates to PineconeVectorStore implementation.
    Future: Can support multiple providers with provider selection logic.
    """
    
    def __init__(self, tenant_id: str):
        self._store = PineconeVectorStore(tenant_id)
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        return await self._store.generate_embedding(text)
    
    async def batch_generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Batch generate embeddings."""
        return await self._store.batch_generate_embeddings(texts)
    
    async def upsert_vector(
        self,
        vector_id: str,
        embedding: List[float],
        metadata: Dict[str, Any],
    ):
        """Upsert a single vector."""
        return await self._store.upsert_vector(vector_id, embedding, metadata)
    
    async def batch_upsert_vectors(self, vectors: List[Dict[str, Any]]):
        """Batch upsert vectors."""
        return await self._store.batch_upsert_vectors(vectors)
    
    async def query_vectors(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filter: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Query vectors."""
        return await self._store.query_vectors(query_embedding, top_k, filter)
    
    async def delete_vectors_by_source(self, source_id: str):
        """Delete all vectors for a source."""
        return await self._store.delete_vectors_by_source(source_id)


