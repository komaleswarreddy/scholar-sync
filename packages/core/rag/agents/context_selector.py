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
        self.max_context_chunks = max_context_chunks
        self.min_relevance_score = min_relevance_score
    
    def select_context(
        self,
        retrieved_chunks: List[Dict[str, Any]],
        query: str,
        max_tokens: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Select relevant context from retrieved chunks.
        
        Args:
            retrieved_chunks: List of retrieved chunk dicts with 'metadata' and 'score'
            query: Original user query
            max_tokens: Optional maximum token limit for context
            
        Returns:
            Selected chunks (filtered and prioritized)
        """
        if not retrieved_chunks:
            return []
        
        # 1. Filter by relevance score
        filtered = [
            chunk for chunk in retrieved_chunks
            if chunk.get("score", 0) >= self.min_relevance_score
        ]
        
        # 2. Sort by score (highest first)
        filtered.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # 3. Remove duplicates (same source_id and similar text)
        selected = []
        seen_texts = set()
        
        for chunk in filtered:
            chunk_text = chunk.get("metadata", {}).get("text", "")
            # Use first 100 chars as fingerprint
            text_fingerprint = chunk_text[:100].lower().strip()
            
            if text_fingerprint not in seen_texts:
                seen_texts.add(text_fingerprint)
                selected.append(chunk)
                
                # Check token limit if specified
                if max_tokens:
                    # Rough estimate: 1 token = 4 characters
                    total_chars = sum(
                        len(c.get("metadata", {}).get("text", ""))
                        for c in selected
                    )
                    if total_chars / 4 > max_tokens:
                        selected.pop()  # Remove last added
                        break
                
                # Check max chunks limit
                if len(selected) >= self.max_context_chunks:
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
