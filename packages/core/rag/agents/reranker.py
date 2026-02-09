"""
Reranker

Reranks retrieved chunks to ensure top chunks answer the query.
Uses cross-encoder or LLM-based reranking.
"""

from typing import List, Dict, Any, Optional
from packages.core.llm import get_llm_client, get_model_for_task


class Reranker:
    """
    Reranks retrieved chunks to improve relevance.
    
    Strategies:
    - Cross-encoder similarity (if available)
    - LLM-based relevance scoring
    - Keyword-based scoring
    """
    
    def __init__(self, tenant_id: str, use_llm: bool = True):
        """
        Initialize reranker.
        
        Args:
            tenant_id: Tenant ID for LLM calls
            use_llm: Whether to use LLM for reranking (more accurate but slower)
        """
        self.tenant_id = tenant_id
        self.use_llm = use_llm
    
    async def rerank(
        self,
        chunks: List[Dict[str, Any]],
        query: str,
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Rerank chunks by relevance to query.
        
        Args:
            chunks: List of chunk dicts with 'metadata' containing 'text'
            query: User query
            top_k: Number of top chunks to return (None = all)
            
        Returns:
            Reranked chunks (most relevant first)
        """
        if not chunks or not query:
            return chunks
        
        if len(chunks) == 1:
            return chunks
        
        if self.use_llm:
            return await self._rerank_with_llm(chunks, query, top_k)
        else:
            return self._rerank_with_keywords(chunks, query, top_k)
    
    async def _rerank_with_llm(
        self,
        chunks: List[Dict[str, Any]],
        query: str,
        top_k: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Rerank using LLM to score relevance."""
        try:
            # Use lightweight model for fast reranking
            provider, model = get_model_for_task("chat")
            llm_client = get_llm_client(provider=provider, model=model, temperature=0.0)
            
            # Build scoring prompt
            chunk_texts = [
                chunk.get("metadata", {}).get("text", "")[:500]  # Limit length
                for chunk in chunks
            ]
            
            prompt = f"""Rate the relevance of each chunk to the query on a scale of 0.0 to 1.0.

Query: {query}

Chunks:
{chr(10).join([f"{i+1}. {text[:200]}..." for i, text in enumerate(chunk_texts)])}

Return ONLY a JSON array of scores in the same order, e.g. [0.9, 0.7, 0.5]:
"""
            
            response = await llm_client.generate(
                prompt=prompt,
                temperature=0.0,
                max_tokens=100,
                tenant_id=self.tenant_id,
                feature="reranker"
            )
            
            # Parse scores
            import json
            import re
            
            content = response.content.strip()
            json_match = re.search(r'\[.*\]', content)
            if json_match:
                scores = json.loads(json_match.group())
                
                # Combine chunks with scores
                scored_chunks = [
                    (chunk, float(score))
                    for chunk, score in zip(chunks, scores[:len(chunks)])
                ]
                
                # Sort by score (highest first)
                scored_chunks.sort(key=lambda x: x[1], reverse=True)
                
                # Return top_k
                reranked = [chunk for chunk, _ in scored_chunks]
                return reranked[:top_k] if top_k else reranked
            else:
                # Fallback to keyword-based
                return self._rerank_with_keywords(chunks, query, top_k)
                
        except Exception as e:
            print(f"[RERANKER] LLM reranking failed: {e}, falling back to keyword-based")
            return self._rerank_with_keywords(chunks, query, top_k)
    
    def _rerank_with_keywords(
        self,
        chunks: List[Dict[str, Any]],
        query: str,
        top_k: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Rerank using keyword matching."""
        query_words = set(query.lower().split())
        
        # Score each chunk
        scored_chunks = []
        for chunk in chunks:
            chunk_text = chunk.get("metadata", {}).get("text", "").lower()
            chunk_words = set(chunk_text.split())
            
            # Calculate overlap
            overlap = len(query_words & chunk_words)
            total_query_words = len(query_words)
            
            # Relevance score
            if total_query_words > 0:
                score = overlap / total_query_words
                # Boost for multiple occurrences
                for word in query_words:
                    count = chunk_text.count(word)
                    if count > 1:
                        score += 0.1 * min(count - 1, 2)
            else:
                score = chunk.get("score", 0.0)
            
            scored_chunks.append((chunk, score))
        
        # Sort by score
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        
        # Return top_k
        reranked = [chunk for chunk, _ in scored_chunks]
        return reranked[:top_k] if top_k else reranked
