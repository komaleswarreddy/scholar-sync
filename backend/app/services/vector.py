"""
Vector Service

Handles all Pinecone vector database operations.
All operations are tenant-scoped using namespaces.
"""

from typing import List, Dict, Any, Optional
# from pinecone import Pinecone, ServerlessSpec
# import openai

from app.core.config import settings

# Initialize Pinecone (lazy initialization)
_pc = None
_index = None

def get_pinecone_index():
    """Lazy initialization of Pinecone index."""
    global _pc, _index
    if _index is None:
        if not settings.PINECONE_API_KEY or settings.PINECONE_API_KEY == "your-pinecone-api-key":
            raise ValueError("Pinecone API key not configured. Please set PINECONE_API_KEY in .env")
        _pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        _index = _pc.Index(settings.PINECONE_INDEX_NAME)
    return _index


class VectorService:
    """
    Service for vector database operations.
    
    All operations use tenant namespace for data isolation:
    - Namespace format: "{tenant_id}"
    - Every query/upsert includes namespace
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.namespace = tenant_id
        self._openai_client = None
    
    @property
    def openai_client(self):
        """Lazy initialization of OpenAI client."""
        if self._openai_client is None:
            if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "your-openai-api-key":
                raise ValueError("OpenAI API key not configured. Please set OPENAI_API_KEY in .env")
            self._openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._openai_client
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using OpenAI.
        
        Uses text-embedding-3-small for cost efficiency.
        """
        response = self.openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
        )
        return response.data[0].embedding
    
    async def batch_generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Batch generate embeddings for multiple texts (much faster!).
        
        OpenAI supports up to 2048 inputs per batch.
        """
        if not texts:
            return []
        
        # Batch in chunks of 100 (safe limit)
        batch_size = 100
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=batch,
            )
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)
        
        return all_embeddings
    
    async def upsert_vector(
        self,
        vector_id: str,
        embedding: List[float],
        metadata: Dict[str, Any],
    ):
        """
        Upsert vector to Pinecone with tenant namespace.
        
        Args:
            vector_id: Unique identifier for vector
            embedding: Vector embedding values
            metadata: Metadata dictionary (source_id, text, etc.)
        """
        index = get_pinecone_index()
        index.upsert(
            vectors=[{
                "id": vector_id,
                "values": embedding,
                "metadata": metadata,
            }],
            namespace=self.namespace,
        )
    
    async def batch_upsert_vectors(self, vectors: List[Dict[str, Any]]):
        """
        Batch upsert vectors to Pinecone (much faster!).
        
        Args:
            vectors: List of dicts with "id", "values", "metadata"
        """
        if not vectors:
            return
        
        index = get_pinecone_index()
        index.upsert(
            vectors=vectors,
            namespace=self.namespace,
        )
    
    async def query_vectors(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filter: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Query vectors from Pinecone with tenant namespace.
        
        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            filter: Optional metadata filter (e.g., {"source_id": {"$in": [...]}})
            
        Returns:
            Query results with matches
        """
        index = get_pinecone_index()
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            namespace=self.namespace,
            filter=filter,
        )
        return results
    
    async def delete_vectors_by_source(self, source_id: str):
        """
        Delete all vectors for a source.
        
        Uses metadata filter to find all chunks for source_id.
        """
        index = get_pinecone_index()
        index.delete(
            filter={"source_id": source_id},
            namespace=self.namespace,
        )

