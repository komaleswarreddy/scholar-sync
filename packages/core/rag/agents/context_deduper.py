"""
Context Deduper

Removes duplicate and near-duplicate chunks before prompt assembly.
Prevents sending redundant context to LLM.
"""

import re
from typing import List, Dict, Any
from difflib import SequenceMatcher


class ContextDeduper:
    """
    Removes duplicate and near-duplicate chunks from context.
    
    Strategies:
    - Remove chunks with >70% similarity
    - Remove near-duplicate paragraphs
    - Remove repeated headings
    """
    
    def __init__(self, similarity_threshold: float = 0.70):
        """
        Initialize context deduper.
        
        Args:
            similarity_threshold: Similarity threshold (0.0-1.0) for removing duplicates
        """
        self.similarity_threshold = similarity_threshold
    
    def dedupe_chunks(
        self,
        chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Remove duplicate and near-duplicate chunks.
        
        Args:
            chunks: List of chunk dicts with 'metadata' containing 'text'
            
        Returns:
            Deduplicated list of chunks
        """
        if not chunks or len(chunks) <= 1:
            return chunks
        
        deduplicated = []
        seen_texts = set()
        
        for chunk in chunks:
            chunk_text = chunk.get("metadata", {}).get("text", "")
            if not chunk_text:
                continue
            
            # Normalize text for comparison
            normalized = self._normalize_text(chunk_text)
            
            # Check for exact duplicates
            if normalized in seen_texts:
                print(f"[DEDUPER] Removed exact duplicate chunk: {chunk.get('id', 'unknown')[:16]}...")
                continue
            
            # Check for near-duplicates (>70% similarity)
            is_duplicate = False
            for seen_text in seen_texts:
                similarity = self._calculate_similarity(normalized, seen_text)
                if similarity > self.similarity_threshold:
                    print(f"[DEDUPER] Removed near-duplicate chunk (similarity: {similarity:.2f}): {chunk.get('id', 'unknown')[:16]}...")
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                # Check for repeated headings
                if not self._is_repeated_heading(chunk_text, deduplicated):
                    deduplicated.append(chunk)
                    seen_texts.add(normalized)
        
        print(f"[DEDUPER] Deduplicated: {len(chunks)} → {len(deduplicated)} chunks")
        return deduplicated
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        # Lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common punctuation variations
        text = text.strip()
        
        return text
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two texts.
        
        Uses SequenceMatcher for similarity calculation.
        """
        return SequenceMatcher(None, text1, text2).ratio()
    
    def _is_repeated_heading(self, chunk_text: str, existing_chunks: List[Dict[str, Any]]) -> bool:
        """
        Check if chunk contains a repeated heading.
        
        Headings are typically:
        - Short lines (1-100 chars)
        - Start with numbers or bullets
        - End with colon or are standalone
        - Appear multiple times
        """
        # Extract potential heading (first line or first 100 chars)
        lines = chunk_text.split('\n')
        if not lines:
            return False
        
        first_line = lines[0].strip()
        
        # Check if it looks like a heading
        is_heading = (
            len(first_line) < 100 and
            (
                first_line.endswith(':') or
                re.match(r'^[\d\.\-\*]+\s+', first_line) or  # Starts with number/bullet
                first_line.isupper() or  # All caps
                (len(first_line.split()) <= 10 and len(first_line) > 5)  # Short phrase
            )
        )
        
        if not is_heading:
            return False
        
        # Check if this heading appears in existing chunks
        heading_normalized = self._normalize_text(first_line)
        for existing_chunk in existing_chunks:
            existing_text = existing_chunk.get("metadata", {}).get("text", "")
            existing_normalized = self._normalize_text(existing_text)
            
            # Check if heading appears in existing chunk
            if heading_normalized in existing_normalized or existing_normalized in heading_normalized:
                # Check if it's at the start of a line (likely a heading)
                if re.search(r'^' + re.escape(heading_normalized) + r'[\s:]', existing_normalized, re.MULTILINE):
                    print(f"[DEDUPER] Removed repeated heading: '{first_line[:50]}...'")
                    return True
        
        return False
    
    def dedupe_paragraphs(self, text: str) -> str:
        """
        Remove duplicate paragraphs from text.
        
        Args:
            text: Text with potential duplicate paragraphs
            
        Returns:
            Text with duplicates removed
        """
        paragraphs = text.split('\n\n')
        seen_paragraphs = set()
        deduplicated_paragraphs = []
        
        for para in paragraphs:
            para_normalized = self._normalize_text(para.strip())
            
            if not para_normalized:
                continue
            
            # Check for duplicates
            is_duplicate = False
            for seen_para in seen_paragraphs:
                similarity = self._calculate_similarity(para_normalized, seen_para)
                if similarity > self.similarity_threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                deduplicated_paragraphs.append(para)
                seen_paragraphs.add(para_normalized)
        
        return '\n\n'.join(deduplicated_paragraphs)
