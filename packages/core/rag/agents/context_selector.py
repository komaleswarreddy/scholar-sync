"""
Context Selection Agent

Selects relevant context from retrieved chunks to avoid over-fetching.
Filters and prioritizes chunks based on query relevance.
"""

from typing import List, Dict, Any, Optional


class ContextSelector:
    """
    Agent that selects relevant context from retrieved chunks.
    
    Prevents over-fetching by:
    - Filtering irrelevant chunks
    - Prioritizing high-relevance chunks
    - Limiting context size
    - Removing duplicates
    """
    
    def __init__(self, max_context_chunks: int = 5, min_relevance_score: float = 0.5):
        """
        Initialize context selector.
        
        Args:
            max_context_chunks: Maximum number of chunks to include
            min_relevance_score: Minimum relevance score threshold
        """
        from config.settings import settings
        self.max_context_chunks = max_context_chunks
        self.min_relevance_score = min_relevance_score
        self.min_chunks = getattr(settings, 'MIN_CONTEXT_CHUNKS', 4)
        self.token_budget = getattr(settings, 'CONTEXT_TOKEN_BUDGET', 2500)
        self.max_chunk_length = getattr(settings, 'MAX_CHUNK_LENGTH', 500)
    
    def select_context(
        self,
        retrieved_chunks: List[Dict[str, Any]],
        query: str,
        max_tokens: Optional[int] = None,
        min_chunks: Optional[int] = None,
        max_chunks: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Select relevant context from retrieved chunks with guardrails.
        
        Args:
            retrieved_chunks: List of retrieved chunk dicts with 'metadata' and 'score'
            query: Original user query
            max_tokens: Optional maximum token limit for context (defaults to token_budget)
            min_chunks: Minimum number of chunks to return (defaults to self.min_chunks)
            
        Returns:
            Selected chunks (filtered and prioritized, ensuring minimum chunks)
        """
        if not retrieved_chunks:
            return []
        
        min_chunks = min_chunks or self.min_chunks
        max_tokens = max_tokens or self.token_budget
        max_chunk_limit = max_chunks if max_chunks is not None else self.max_context_chunks
        
        # 1. Filter by relevance score (but be lenient to ensure we have enough chunks)
        # Lower threshold if we don't have enough chunks
        filtered = [
            chunk for chunk in retrieved_chunks
            if chunk.get("score", 0) >= self.min_relevance_score
        ]
        
        # If filtered results are too few, lower threshold
        if len(filtered) < min_chunks:
            lowered_threshold = max(0.25, self.min_relevance_score - 0.2)
            filtered = [
                chunk for chunk in retrieved_chunks
                if chunk.get("score", 0) >= lowered_threshold
            ]

        # If still empty (e.g. LlamaIndex/Pinecone scores are very low but chunks are relevant),
        # use best-effort top chunks so the LLM always receives *some* evidence from retrieval.
        if not filtered and retrieved_chunks:
            retrieved_sorted = sorted(
                retrieved_chunks,
                key=lambda c: float(c.get("score", 0) or 0),
                reverse=True,
            )
            take_n = min(
                max(min_chunks, min(max_chunk_limit, len(retrieved_sorted))),
                len(retrieved_sorted),
            )
            filtered = retrieved_sorted[:take_n]
        
        # 2. Sort by score (highest first) - prioritize by rerank score if available
        def get_sort_score(chunk):
            # Prefer rerank_score if available, otherwise use score
            rerank_score = chunk.get("metadata", {}).get("rerank_score")
            if rerank_score is not None:
                return rerank_score
            return chunk.get("score", 0)
        
        filtered.sort(key=get_sort_score, reverse=True)
        
        # 3. Remove duplicates (same source_id and similar text)
        selected = []
        seen_texts = set()
        seen_chunk_ids = set()
        
        def estimate_tokens(text: str) -> int:
            """Rough token estimation: 1 token ≈ 4 characters."""
            return len(text) // 4
        
        def get_adjacent_chunks(chunk_id: str, source_id: str) -> List[Dict[str, Any]]:
            """Find adjacent chunks from the same source (for continuity)."""
            adjacent = []
            # Look for chunks with sequential IDs or similar metadata
            # This is a simplified version - in production, you'd check chunk indices
            return adjacent
        
        total_tokens = 0
        
        for chunk in filtered:
            chunk_id = chunk.get("id", "")
            chunk_text = chunk.get("metadata", {}).get("text", "")
            source_id = chunk.get("metadata", {}).get("source_id", "")
            
            # Skip if already selected
            if chunk_id in seen_chunk_ids:
                continue
            
            # Use first 100 chars as fingerprint for duplicate detection
            text_fingerprint = chunk_text[:100].lower().strip()
            
            if text_fingerprint not in seen_texts:
                chunk_tokens = estimate_tokens(chunk_text)
                
                # Check if adding this chunk would exceed token budget
                if total_tokens + chunk_tokens > max_tokens and len(selected) >= min_chunks:
                    # We have minimum chunks and would exceed budget, stop
                    break
                
                seen_texts.add(text_fingerprint)
                seen_chunk_ids.add(chunk_id)
                selected.append(chunk)
                total_tokens += chunk_tokens
                
                # Try to include adjacent chunks for continuity (if within budget)
                if len(selected) < max_chunk_limit:
                    adjacent = get_adjacent_chunks(chunk_id, source_id)
                    for adj_chunk in adjacent:
                        if adj_chunk.get("id") not in seen_chunk_ids:
                            adj_text = adj_chunk.get("metadata", {}).get("text", "")
                            adj_tokens = estimate_tokens(adj_text)
                            if total_tokens + adj_tokens <= max_tokens and len(selected) < max_chunk_limit:
                                selected.append(adj_chunk)
                                seen_chunk_ids.add(adj_chunk.get("id"))
                                total_tokens += adj_tokens
                
                # Check max chunks limit
                if len(selected) >= max_chunk_limit:
                    break
        
        # Guardrail: Ensure we have minimum chunks (even if lower relevance)
        if len(selected) < min_chunks and len(retrieved_chunks) >= min_chunks:
            # Add more chunks to meet minimum, even if they have lower scores
            for chunk in filtered:
                if chunk.get("id") not in seen_chunk_ids:
                    chunk_tokens = estimate_tokens(chunk.get("metadata", {}).get("text", ""))
                    if total_tokens + chunk_tokens <= max_tokens * 1.2:  # Allow 20% over budget for minimum
                        selected.append(chunk)
                        seen_chunk_ids.add(chunk.get("id"))
                        total_tokens += chunk_tokens
                        if len(selected) >= min_chunks:
                            break
        
        return selected
    
    def calculate_relevance(
        self,
        chunk_text: str,
        query: str
    ) -> float:
        """
        Calculate relevance score between chunk and query.
        
        Args:
            chunk_text: Chunk text content
            query: User query
            
        Returns:
            Relevance score (0.0 to 1.0)
        """
        # Simple keyword-based relevance
        query_words = set(query.lower().split())
        chunk_words = set(chunk_text.lower().split())
        
        # Calculate overlap
        overlap = len(query_words & chunk_words)
        total_query_words = len(query_words)
        
        if total_query_words == 0:
            return 0.0
        
        # Basic relevance score
        relevance = overlap / total_query_words
        
        # Boost if query words appear multiple times
        chunk_lower = chunk_text.lower()
        for word in query_words:
            count = chunk_lower.count(word)
            if count > 1:
                relevance += 0.1 * min(count - 1, 2)  # Cap boost at 0.2
        
        return min(relevance, 1.0)
