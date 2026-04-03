"""
Hybrid Retriever

Combines vector search (semantic) with keyword search (BM25-like) for better retrieval.
Ensures relevant chunks appear in top results.
"""

from typing import List, Dict, Any, Optional
from collections.abc import Mapping
from collections import Counter
import math


class HybridRetriever:
    """
    Hybrid retrieval combining vector and keyword search.
    
    Strategy:
    1. Perform vector search (semantic similarity)
    2. Perform keyword search (BM25-like scoring)
    3. Combine and rerank results
    """
    
    def __init__(self, vector_weight: float = 0.7, keyword_weight: float = 0.3):
        """
        Initialize hybrid retriever.
        
        Args:
            vector_weight: Weight for vector search scores (0.0 to 1.0)
            keyword_weight: Weight for keyword search scores (0.0 to 1.0)
        """
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
    
    def combine_results(
        self,
        vector_results: List[Dict[str, Any]],
        query: str,
        all_chunks: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Combine vector and keyword search results.
        
        Args:
            vector_results: Results from vector search (with 'score' and 'metadata')
            query: User query
            all_chunks: Optional all chunks for keyword search (if not provided, uses vector_results)
            
        Returns:
            Combined and reranked results
        """
        if not vector_results:
            return []

        def _mget(obj: Any, key: str, default: Any = None) -> Any:
            if obj is None:
                return default
            if isinstance(obj, Mapping):
                return obj.get(key, default)
            # Some SDK objects are dict-like (have .get) but are not dict subclasses.
            getter = getattr(obj, "get", None)
            if callable(getter):
                try:
                    return getter(key, default)
                except Exception:
                    return default
            return default

        def _as_dict(obj: Any) -> Dict[str, Any]:
            if obj is None:
                return {}
            if isinstance(obj, dict):
                return obj
            if isinstance(obj, Mapping):
                return dict(obj)
            # Best-effort for pinecone match objects
            return {
                "id": _mget(obj, "id", ""),
                "score": _mget(obj, "score", 0.0),
                "metadata": _mget(obj, "metadata", {}) or {},
            }
        
        # Use vector results for keyword search if all_chunks not provided
        chunks_to_search = all_chunks if all_chunks else vector_results
        
        # Calculate keyword scores
        keyword_scores = self._calculate_keyword_scores(chunks_to_search, query)
        
        # Create chunk ID to scores mapping
        chunk_scores = {}
        for chunk in vector_results:
            # Skip None or invalid chunks
            if not chunk:
                continue
                
            chunk_id = _mget(chunk, "id", "")
            if not chunk_id:
                continue
                
            vector_score = _mget(chunk, "score", 0.0) or 0.0
            keyword_score = keyword_scores.get(chunk_id, 0.0)
            
            # Normalize scores to 0-1 range
            # Vector scores are already 0-1 (cosine similarity)
            # Keyword scores need normalization
            max_keyword = max(keyword_scores.values()) if keyword_scores.values() else 1.0
            normalized_keyword = keyword_score / max_keyword if max_keyword > 0 else 0.0
            
            # Combined score
            combined_score = (
                self.vector_weight * vector_score +
                self.keyword_weight * normalized_keyword
            )
            
            chunk_scores[chunk_id] = {
                "chunk": _as_dict(chunk),
                "vector_score": vector_score,
                "keyword_score": normalized_keyword,
                "combined_score": combined_score
            }
        
        # Sort by combined score
        sorted_chunks = sorted(
            chunk_scores.values(),
            key=lambda x: x["combined_score"],
            reverse=True
        )
        
        # Return chunks with updated scores
        result = []
        for item in sorted_chunks:
            chunk = item.get("chunk")
            # Skip if chunk is None or not a dict
            if chunk is None or not isinstance(chunk, dict):
                continue
                
            # Create a copy of the chunk dict
            chunk_copy = dict(chunk)  # Use dict() instead of .copy() for safety
            chunk_copy["score"] = item["combined_score"]
            chunk_copy["metadata"] = chunk_copy.get("metadata", {})
            chunk_copy["metadata"]["vector_score"] = item["vector_score"]
            chunk_copy["metadata"]["keyword_score"] = item["keyword_score"]
            result.append(chunk_copy)
        
        return result
    
    def _calculate_keyword_scores(
        self,
        chunks: List[Dict[str, Any]],
        query: str
    ) -> Dict[str, float]:
        """
        Calculate BM25-like keyword scores for chunks.
        
        Args:
            chunks: List of chunk dicts with 'metadata' containing 'text'
            query: User query
            
        Returns:
            Dict mapping chunk_id to keyword score
        """
        query_terms = query.lower().split()
        if not query_terms:
            return {}
        
        # Calculate term frequencies and document frequencies
        chunk_texts = {}
        term_frequencies = {}  # term -> {chunk_id: count}
        doc_frequencies = {}  # term -> number of docs containing it
        
        def _keyword_text(md: Dict[str, Any]) -> str:
            """
            Contextual Retrieval: keyword scoring should include contextual metadata
            (context/summary/hints) to improve lexical recall, while citations remain
            based on metadata['text'] (raw chunk).
            """
            raw = str(md.get("text", "") or "")
            ctx = str(md.get("chunk_context", "") or "")
            summ = str(md.get("chunk_summary", "") or "")
            hint = str(md.get("concept_hint", "") or "")
            # Compact concatenation; if contextual fields absent, this is just raw.
            return "\n".join([ctx, summ, hint, raw]).strip()

        def _mget(obj: Any, key: str, default: Any = None) -> Any:
            if obj is None:
                return default
            if isinstance(obj, Mapping):
                return obj.get(key, default)
            getter = getattr(obj, "get", None)
            if callable(getter):
                try:
                    return getter(key, default)
                except Exception:
                    return default
            return default

        for chunk in chunks:
            if not chunk:
                continue
            chunk_id = _mget(chunk, "id", "")
            md = _mget(chunk, "metadata", {}) or {}
            chunk_text = _keyword_text(md).lower()
            chunk_texts[chunk_id] = chunk_text
            
            # Count term frequencies in this chunk
            words = chunk_text.split()
            word_counts = Counter(words)
            
            for term in query_terms:
                if term in word_counts:
                    if term not in term_frequencies:
                        term_frequencies[term] = {}
                    term_frequencies[term][chunk_id] = word_counts[term]
                    
                    if term not in doc_frequencies:
                        doc_frequencies[term] = 0
                    doc_frequencies[term] += 1
        
        # Calculate BM25-like scores
        total_chunks = len(chunks)
        avg_chunk_length = sum(len(text.split()) for text in chunk_texts.values()) / total_chunks if total_chunks > 0 else 1
        k1 = 1.5  # BM25 parameter
        b = 0.75  # BM25 parameter
        
        scores = {}
        for chunk_id, chunk_text in chunk_texts.items():
            words = chunk_text.split()
            chunk_length = len(words)
            
            score = 0.0
            for term in query_terms:
                if term in term_frequencies and chunk_id in term_frequencies[term]:
                    tf = term_frequencies[term][chunk_id]
                    df = doc_frequencies.get(term, 1)
                    
                    # IDF (inverse document frequency)
                    idf = math.log((total_chunks - df + 0.5) / (df + 0.5) + 1.0)
                    
                    # BM25 score component
                    numerator = tf * (k1 + 1)
                    denominator = tf + k1 * (1 - b + b * (chunk_length / avg_chunk_length))
                    bm25_component = idf * (numerator / denominator)
                    
                    score += bm25_component
            
            scores[chunk_id] = score
        
        return scores
    
    async def hybrid_search(
        self,
        query: str,
        query_embedding: List[float],
        vector_store,
        top_k: int = 10,
        filter: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search (vector + keyword).
        
        Args:
            query: User query text
            query_embedding: Query vector embedding
            vector_store: Vector store instance
            top_k: Number of results
            filter: Optional metadata filter
            
        Returns:
            Combined search results
        """
        # 1. Vector search
        vector_results = await vector_store.query_vectors(
            query_embedding=query_embedding,
            top_k=top_k * 2,  # Get more for keyword filtering
            filter=filter
        )
        
        vector_matches = vector_results.get("matches", [])
        
        # 2. Combine with keyword search
        combined = self.combine_results(vector_matches, query)
        
        # 3. Return top_k
        return combined[:top_k]
