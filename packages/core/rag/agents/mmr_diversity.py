"""
MMR (Maximal Marginal Relevance) Diversity Enforcement

Ensures retrieved chunks are diverse and avoid duplicate sections.
Uses MMR algorithm to balance relevance and diversity.
"""

from typing import List, Dict, Any, Optional
import numpy as np


class MMRDiversity:
    """
    Implements MMR (Maximal Marginal Relevance) for diverse chunk selection.
    
    MMR balances:
    - Relevance to query (lambda * sim(query, doc))
    - Diversity from already selected docs ((1 - lambda) * max sim(doc, selected))
    
    Formula: MMR = argmax[λ * sim(query, doc) - (1-λ) * max sim(doc, selected)]
    """
    
    def __init__(self, lambda_param: float = 0.7):
        """
        Initialize MMR diversity selector.
        
        Args:
            lambda_param: Balance between relevance (1.0) and diversity (0.0)
                - 1.0 = pure relevance (no diversity)
                - 0.0 = pure diversity (no relevance)
                - 0.7 = balanced (default)
        """
        self.lambda_param = lambda_param
    
    def select_diverse_chunks(
        self,
        chunks: List[Dict[str, Any]],
        query_embedding: List[float],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Select diverse chunks using MMR algorithm.
        
        Args:
            chunks: List of chunk dicts with 'values' (embedding) and 'score'
            query_embedding: Query vector embedding
            top_k: Number of chunks to select
            
        Returns:
            Selected diverse chunks
        """
        if not chunks or top_k <= 0:
            return []
        
        if len(chunks) <= top_k:
            return chunks
        
        # Convert to numpy for efficient computation
        query_vec = np.array(query_embedding)
        
        # Extract embeddings and metadata
        chunk_embeddings = []
        chunk_metadata = []
        for chunk in chunks:
            if "values" in chunk:
                chunk_embeddings.append(chunk["values"])
                chunk_metadata.append(chunk)
            elif "metadata" in chunk and "embedding" in chunk["metadata"]:
                chunk_embeddings.append(chunk["metadata"]["embedding"])
                chunk_metadata.append(chunk)
            else:
                # Fallback: use score as proxy
                chunk_embeddings.append(None)
                chunk_metadata.append(chunk)
        
        # Filter out chunks without embeddings
        valid_chunks = [
            (emb, meta) for emb, meta in zip(chunk_embeddings, chunk_metadata)
            if emb is not None
        ]
        
        if not valid_chunks:
            # Fallback: return top-k by score
            return sorted(chunks, key=lambda x: x.get("score", 0), reverse=True)[:top_k]
        
        embeddings, metadata = zip(*valid_chunks)
        embeddings = np.array(embeddings)
        
        # Calculate relevance scores (cosine similarity to query)
        query_norm = np.linalg.norm(query_vec)
        if query_norm == 0:
            # Fallback to score-based selection
            return sorted(chunks, key=lambda x: x.get("score", 0), reverse=True)[:top_k]
        
        relevance_scores = np.dot(embeddings, query_vec) / (
            np.linalg.norm(embeddings, axis=1) * query_norm
        )
        
        # MMR selection
        selected_indices = []
        selected_embeddings = []
        
        # Start with most relevant chunk
        first_idx = np.argmax(relevance_scores)
        selected_indices.append(first_idx)
        selected_embeddings.append(embeddings[first_idx])
        
        # Select remaining chunks using MMR
        remaining_indices = [i for i in range(len(embeddings)) if i != first_idx]
        
        while len(selected_indices) < top_k and remaining_indices:
            best_mmr_score = -float('inf')
            best_idx = None
            
            for idx in remaining_indices:
                chunk_emb = embeddings[idx]
                
                # Relevance component
                relevance = relevance_scores[idx]
                
                # Diversity component (max similarity to already selected)
                if selected_embeddings:
                    similarities = np.dot(
                        np.array(selected_embeddings),
                        chunk_emb
                    ) / (
                        np.linalg.norm(selected_embeddings, axis=1) *
                        np.linalg.norm(chunk_emb)
                    )
                    max_similarity = np.max(similarities)
                else:
                    max_similarity = 0.0
                
                # MMR score
                mmr_score = (
                    self.lambda_param * relevance -
                    (1 - self.lambda_param) * max_similarity
                )
                
                if mmr_score > best_mmr_score:
                    best_mmr_score = mmr_score
                    best_idx = idx
            
            if best_idx is not None:
                selected_indices.append(best_idx)
                selected_embeddings.append(embeddings[best_idx])
                remaining_indices.remove(best_idx)
            else:
                break
        
        # Return selected chunks in order
        selected_chunks = [metadata[i] for i in selected_indices]
        return selected_chunks
    
    def remove_duplicate_sections(
        self,
        chunks: List[Dict[str, Any]],
        similarity_threshold: float = 0.85
    ) -> List[Dict[str, Any]]:
        """
        Remove chunks that are too similar to each other.
        
        Args:
            chunks: List of chunk dicts
            similarity_threshold: Threshold for considering chunks duplicates
            
        Returns:
            Filtered chunks with duplicates removed
        """
        if len(chunks) <= 1:
            return chunks
        
        filtered = []
        seen_embeddings = []
        
        for chunk in chunks:
            chunk_emb = None
            if "values" in chunk:
                chunk_emb = chunk["values"]
            elif "metadata" in chunk and "embedding" in chunk["metadata"]:
                chunk_emb = chunk["metadata"]["embedding"]
            
            if chunk_emb is None:
                # No embedding, include it (can't check similarity)
                filtered.append(chunk)
                continue
            
            # Check similarity to already selected chunks
            is_duplicate = False
            for seen_emb in seen_embeddings:
                similarity = np.dot(chunk_emb, seen_emb) / (
                    np.linalg.norm(chunk_emb) * np.linalg.norm(seen_emb)
                )
                if similarity >= similarity_threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                filtered.append(chunk)
                seen_embeddings.append(chunk_emb)
        
        return filtered
