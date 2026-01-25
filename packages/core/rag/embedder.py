"""
Embedder

Handles text embedding generation for RAG pipeline.
Currently delegates to vector store implementation.
"""

from typing import List
from packages.core.rag.vectorstores.pinecone_store import PineconeVectorStore


class Embedder:
    """
    Service for generating text embeddings.
    
    Currently uses OpenAI embeddings via PineconeVectorStore.
    Future: Can support multiple embedding providers.
    """
    
    def __init__(self, tenant_id: str):
        self.vector_store = PineconeVectorStore(tenant_id)
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        return await self.vector_store.generate_embedding(text)
    
    async def batch_generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Batch generate embeddings for multiple texts."""
        return await self.vector_store.batch_generate_embeddings(texts)


