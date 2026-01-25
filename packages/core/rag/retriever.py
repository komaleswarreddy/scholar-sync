"""
Retriever

Handles retrieval of relevant chunks from vector store for RAG pipeline.
"""

from typing import List, Dict, Any, Optional
from config.settings import settings
from packages.core.rag.vectorstores.pinecone_store import PineconeVectorStore


class Retriever:
    """
    Service for retrieving relevant chunks from vector store.
    """
    
    def __init__(self, tenant_id: str):
        self.vector_store = PineconeVectorStore(tenant_id)
    
    async def retrieve(
        self,
        query_embedding: List[float],
        top_k: int = None,
        filter: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve relevant chunks from vector store.
        
        Args:
            query_embedding: Query vector embedding
            top_k: Number of results (defaults to settings.TOP_K_CHUNKS)
            filter: Optional metadata filter
            
        Returns:
            Query results with matches
        """
        top_k = top_k or settings.TOP_K_CHUNKS
        return await self.vector_store.query_vectors(
            query_embedding=query_embedding,
            top_k=top_k,
            filter=filter,
        )


