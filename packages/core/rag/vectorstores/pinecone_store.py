"""
Pinecone Vector Store Implementation

Handles all Pinecone vector database operations.
All operations are tenant-scoped using namespaces.
"""

from typing import List, Dict, Any, Optional
import asyncio
import time

try:
    from pinecone import Pinecone, ServerlessSpec
except ImportError:
    Pinecone = None
    ServerlessSpec = None
    print("[WARNING] Pinecone package not installed. Install with: pip install pinecone-client")

try:
    import openai
    import httpx
except ImportError:
    openai = None
    httpx = None
    print("[WARNING] OpenAI package not installed. Install with: pip install openai")

from config.settings import settings
from packages.core.rag.vectorstores.base import BaseVectorStore
from packages.core.rag.vectorstores.namespace import normalize_pinecone_namespace  # re-export

# Initialize Pinecone (lazy initialization)
_pc = None
_index = None

def get_pinecone_index():
    """Lazy initialization of Pinecone index."""
    global _pc, _index
    if _index is None:
        if Pinecone is None:
            raise ValueError("Pinecone package not installed. Please install with: pip install pinecone-client")
        if not settings.PINECONE_API_KEY or settings.PINECONE_API_KEY == "your-pinecone-api-key":
            raise ValueError("Pinecone API key not configured. Please set PINECONE_API_KEY in .env")
        _pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        _index = _pc.Index(settings.PINECONE_INDEX_NAME)
    return _index


class PineconeVectorStore(BaseVectorStore):
    """
    Pinecone implementation of vector store.
    
    All operations use tenant namespace for data isolation:
    - Namespace format: "{tenant_id}"
    - Every query/upsert includes namespace
    
    Optional ``namespace_override`` (e.g. NcertDataGlobal) and embedding overrides
    support admin global corpus and query-time retrieval without changing tenant defaults.
    """
    
    def __init__(
        self,
        tenant_id: str,
        *,
        namespace_override: Optional[str] = None,
        embedding_model_override: Optional[str] = None,
        embedding_dimensions_override: Optional[int] = None,
    ):
        super().__init__(tenant_id)
        if namespace_override is not None:
            self.namespace = namespace_override
        self._embedding_model_override = embedding_model_override
        self._embedding_dimensions_override = embedding_dimensions_override
        self._openai_client = None

    def _embedding_model(self) -> str:
        return self._embedding_model_override or settings.OPENAI_EMBEDDING_MODEL

    def _embedding_dimensions(self) -> int:
        return (
            self._embedding_dimensions_override
            if self._embedding_dimensions_override is not None
            else settings.OPENAI_EMBEDDING_DIMENSIONS
        )
    
    @property
    def openai_client(self):
        """Lazy initialization of OpenAI client."""
        if self._openai_client is None:
            if openai is None:
                raise ValueError("OpenAI package not installed. Please install with: pip install openai")
            if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "your-openai-api-key":
                raise ValueError("OpenAI API key not configured. Please set OPENAI_API_KEY in .env")
            
            # Workaround for OpenAI 1.9.0/1.10.0 bug with httpx proxies parameter
            # Create a custom httpx client without proxies to avoid the compatibility issue
            try:
                if httpx is not None:
                    # Create httpx client explicitly (without proxies) and pass to OpenAI
                    # This bypasses OpenAI's internal client creation that tries to pass 'proxies'
                    http_client = httpx.Client(timeout=60.0)
                    self._openai_client = openai.OpenAI(
                        api_key=settings.OPENAI_API_KEY,
                        http_client=http_client,
                    )
                else:
                    # Fallback: try without custom http_client
                    self._openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            except Exception as e:
                # If custom client fails, try standard initialization
                if 'proxies' in str(e).lower():
                    # Last resort: try with AsyncClient or different approach
                    self._openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                else:
                    raise
        return self._openai_client
    
    async def generate_embedding(
        self,
        text: str,
        *,
        metrics_user_id: Optional[str] = None,
        metrics_feature_tag: Optional[str] = None,
    ) -> List[float]:
        """
        Generate embedding for text using OpenAI.
        
        Uses text-embedding-3-small for cost efficiency.
        """
        embedding_model = self._embedding_model()
        embedding_dimensions = self._embedding_dimensions()
        print(f"[RAG] Generating embedding: Provider=OpenAI, Model={embedding_model}, TextLength={len(text)} chars")
        t0 = time.perf_counter()
        response = await asyncio.to_thread(
            self.openai_client.embeddings.create,
            model=embedding_model,
            input=text,
            dimensions=embedding_dimensions,
        )
        latency_ms = (time.perf_counter() - t0) * 1000
        embedding_dim = len(response.data[0].embedding)
        print(f"[RAG] Embedding generated: Dimension={embedding_dim}")

        if metrics_user_id and metrics_feature_tag:
            try:
                from packages.core.guardrails.cost_manager import get_cost_manager

                usage = getattr(response, "usage", None)
                pt = int(getattr(usage, "prompt_tokens", 0) or 0) if usage else 0
                tt = int(getattr(usage, "total_tokens", 0) or 0) if usage else 0
                if pt <= 0 and tt > 0:
                    pt = tt
                if pt <= 0:
                    pt = max(1, int(len(text) / 4))
                cm = get_cost_manager()
                await cm.record_usage(
                    tenant_id=str(self.tenant_id),
                    user_id=str(metrics_user_id),
                    model=embedding_model,
                    provider="openai",
                    prompt_tokens=pt,
                    completion_tokens=0,
                    feature_tag=metrics_feature_tag,
                    latency_ms=latency_ms,
                )
            except Exception:
                pass

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
            response = await asyncio.to_thread(
                self.openai_client.embeddings.create,
                model=self._embedding_model(),
                input=batch,
                dimensions=self._embedding_dimensions(),
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
        
        Uses metadata filter on `source_id` (string UUID). Pinecone serverless expects
        explicit operators for some deployments; we try $eq first, then legacy form.
        """
        try:
            index = get_pinecone_index()
            last_err: Optional[Exception] = None
            for flt in (
                {"source_id": {"$eq": str(source_id)}},
                {"source_id": str(source_id)},
            ):
                try:
                    index.delete(filter=flt, namespace=self.namespace)
                    print(
                        f"[VECTOR] Deleted vectors for source {source_id} in namespace {self.namespace} "
                        f"(filter={list(flt.keys())})"
                    )
                    return
                except Exception as e:
                    last_err = e
                    continue
            if last_err:
                raise last_err
        except ValueError as e:
            # Pinecone not configured - log and continue
            print(f"[WARNING] [VECTOR] Pinecone not configured, skipping vector deletion: {str(e)}")
            raise
        except Exception as e:
            import traceback
            print(f"[ERROR] [VECTOR] Failed to delete vectors for source {source_id}: {type(e).__name__}: {str(e)}")
            print(f"[ERROR] [VECTOR] Traceback: {traceback.format_exc()}")
            raise


