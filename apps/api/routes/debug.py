"""
Debug API Routes

Provides debug endpoints for RAG pipeline tracing and diagnostics.
"""

from fastapi import APIRouter, Request, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from packages.core.database.connection import get_db
from packages.core.rag.retriever import Retriever
from packages.core.rag.embedder import Embedder
from config.settings import settings

router = APIRouter()


@router.get("/retrieval_trace")
async def get_retrieval_trace(
    request: Request,
    query: str = Query(..., description="Query to trace through retrieval pipeline"),
    top_k: int = Query(10, description="Number of chunks to retrieve"),
    db: AsyncSession = Depends(get_db),
):
    """
    Debug endpoint to trace a query through the full retrieval pipeline.
    
    Returns detailed trace of:
    - Original query
    - Rewritten queries
    - Detected intent
    - Retrieved chunks at each stage
    - Final chunks sent to LLM
    - Guardrails applied
    """
    tenant_id = request.state.tenant_id
    
    if not settings.RAG_DEBUG:
        raise HTTPException(
            status_code=403,
            detail="RAG_DEBUG must be enabled to use this endpoint. Set RAG_DEBUG=true in .env"
        )
    
    # Create retriever
    retriever = Retriever(tenant_id)
    
    # Perform retrieval with debug trace
    try:
        results = await retriever.retrieve(
            query=query,
            top_k=top_k,
            filter=None,
            conversation_history=None,
        )
        
        # Extract debug trace
        debug_trace = results.get("debug_trace", {})
        
        # Add additional metadata
        debug_trace["settings"] = {
            "use_retrieval_agents": settings.USE_RETRIEVAL_AGENTS,
            "mmr_lambda": settings.MMR_LAMBDA,
            "hybrid_vector_weight": settings.HYBRID_VECTOR_WEIGHT,
            "hybrid_keyword_weight": settings.HYBRID_KEYWORD_WEIGHT,
            "max_context_chunks": settings.MAX_CONTEXT_CHUNKS,
            "min_context_chunks": settings.MIN_CONTEXT_CHUNKS,
            "use_llm_reranking": settings.USE_LLM_RERANKING,
            "query_rewrite_confidence_threshold": settings.QUERY_REWRITE_CONFIDENCE_THRESHOLD,
            "context_token_budget": settings.CONTEXT_TOKEN_BUDGET,
        }
        
        # Add final chunk details
        final_chunks = results.get("matches", [])
        debug_trace["final_chunks_details"] = [
            {
                "id": chunk.get("id"),
                "score": chunk.get("score"),
                "rerank_score": chunk.get("metadata", {}).get("rerank_score"),
                "vector_score": chunk.get("metadata", {}).get("vector_score"),
                "keyword_score": chunk.get("metadata", {}).get("keyword_score"),
                "text_preview": chunk.get("metadata", {}).get("text", "")[:200],
                "source_id": chunk.get("metadata", {}).get("source_id"),
            }
            for chunk in final_chunks
        ]
        
        return {
            "tenant_id": tenant_id,
            "query": query,
            "trace": debug_trace,
            "summary": {
                "total_retrieved": debug_trace.get("retrieved_chunks_initial", {}).get("count", 0),
                "final_count": len(final_chunks),
                "token_size": debug_trace.get("final_chunks_sent_to_llm", {}).get("token_size", 0),
                "guardrails_applied": debug_trace.get("guardrails_applied", []),
            }
        }
        
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"Error during retrieval trace: {str(e)}\n{traceback.format_exc()}"
        )
