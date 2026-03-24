"""
Base Vector Store Interface

Abstract base class for all vector store implementations.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from packages.core.rag.vectorstores.namespace import normalize_pinecone_namespace


class BaseVectorStore(ABC):
    """
    Abstract base class for vector store implementations.
    
    All vector stores must implement this interface to ensure
    consistent behavior across different providers.
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.namespace = normalize_pinecone_namespace(tenant_id)
    
    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        pass
    
    @abstractmethod
    async def batch_generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Batch generate embeddings for multiple texts."""
        pass
    
    @abstractmethod
    async def upsert_vector(
        self,
        vector_id: str,
        embedding: List[float],
        metadata: Dict[str, Any],
    ):
        """Upsert a single vector."""
        pass
    
    @abstractmethod
    async def batch_upsert_vectors(self, vectors: List[Dict[str, Any]]):
        """Batch upsert vectors."""
        pass
    
    @abstractmethod
    async def query_vectors(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filter: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Query vectors."""
        pass
    
    @abstractmethod
    async def delete_vectors_by_source(self, source_id: str):
        """Delete all vectors for a source."""
        pass


