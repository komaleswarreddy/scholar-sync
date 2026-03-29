"""
Embedder

Handles text embedding generation for RAG pipeline.
Currently delegates to vector store implementation.
"""

from typing import List, Optional
from packages.core.rag.vectorstores.pinecone_store import PineconeVectorStore


class Embedder:
    """
    Service for generating text embeddings.
    
    Currently uses OpenAI embeddings via PineconeVectorStore.
    Future: Can support multiple embedding providers.
    """
    
    def __init__(self, tenant_id: str, user_id: Optional[str] = None):
        self.tenant_id = tenant_id
        self.vector_store = PineconeVectorStore(tenant_id)
        self.user_id = user_id
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        return await self.vector_store.generate_embedding(
            text,
            metrics_user_id=self.user_id,
            metrics_feature_tag="embedding" if self.user_id else None,
        )
    
    async def batch_generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Batch generate embeddings for multiple texts."""
        return await self.vector_store.batch_generate_embeddings(texts)


