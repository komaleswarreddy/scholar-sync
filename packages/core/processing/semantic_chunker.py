"""
Semantic Chunker

Creates readable standalone chunks using semantic boundaries.
Splits at paragraphs, sentences, and clauses to ensure chunks are meaningful.
"""

import re
from typing import List, Tuple, Dict, Optional


class SemanticChunker:
    """
    Semantic chunking that creates readable standalone chunks.
    
    Strategy:
    1. Split by paragraphs (double newlines) first
    2. If paragraphs too large, split by sentences
    3. If sentences too large, split by clauses
    4. Maintains minimum chunk size (25% of target)
    """
    
    def __init__(self, min_chunk_size_ratio: float = 0.25):
        """
        Initialize semantic chunker.
        
        Args:
            min_chunk_size_ratio: Minimum chunk size as ratio of target (default: 0.25 = 25%)
        """
        self.min_chunk_size_ratio = min_chunk_size_ratio
        
        # Sentence ending patterns
        self.sentence_endings = re.compile(r'[.!?]\s+')
        
        # Clause separators (commas, semicolons, colons)
        self.clause_separators = re.compile(r'[,;:]\s+')
    
    def chunk_text(
        self,
        text: str,
        chunk_size: int = 1000,
        overlap: int = 0,
        pages: Optional[List[Tuple[int, str]]] = None
    ) -> List[Tuple[str, Dict]]:
        """
        Split text into semantic chunks with metadata.
        
        Args:
            text: Input text to chunk
            chunk_size: Target chunk size in characters
            overlap: Overlap between chunks in characters
            pages: Optional list of (page_num, page_text) tuples for page metadata
            
        Returns:
            List of (chunk_text, metadata) tuples where metadata includes:
            - chunk_index: Index of chunk
            - page_start: Starting page number
            - page_end: Ending page number
            - char_start: Starting character position
            - char_end: Ending character position
        """
        if not text:
            return []
        
        min_chunk_size = int(chunk_size * self.min_chunk_size_ratio)
        
        # If pages provided, chunk with page awareness
        if pages:
            return self._chunk_with_pages(pages, chunk_size, overlap, min_chunk_size)
        
        # Otherwise, chunk entire text
        return self._chunk_text_semantic(text, chunk_size, overlap, min_chunk_size)
    
    def _chunk_with_pages(
        self,
        pages: List[Tuple[int, str]],
        chunk_size: int,
        overlap: int,
        min_chunk_size: int
    ) -> List[Tuple[str, Dict]]:
        """Chunk text with page awareness for metadata."""
        chunks = []
        chunk_index = 0
        current_chunk = ""
        current_page_start = None
        current_page_end = None
        char_offset = 0
        
        for page_num, page_text in pages:
            if not page_text.strip():
                continue
            
            # Try to add this page to current chunk
            if len(current_chunk) + len(page_text) <= chunk_size:
                # Page fits in current chunk
                if current_chunk:
                    current_chunk += "\n\n" + page_text
                else:
                    current_chunk = page_text
                    current_page_start = page_num
                current_page_end = page_num
            else:
                # Page doesn't fit, finalize current chunk
                if current_chunk:
                    chunks.append((
                        current_chunk,
                        {
                            "chunk_index": chunk_index,
                            "page_start": current_page_start,
                            "page_end": current_page_end,
                            "char_start": char_offset,
                            "char_end": char_offset + len(current_chunk),
                        }
                    ))
                    chunk_index += 1
                    char_offset += len(current_chunk) - overlap
                
                # Start new chunk with this page
                # If page is too large, split it semantically
                if len(page_text) > chunk_size:
                    page_chunks = self._chunk_text_semantic(
                        page_text, chunk_size, overlap, min_chunk_size
                    )
                    for i, (chunk_text, _) in enumerate(page_chunks):
                        chunks.append((
                            chunk_text,
                            {
                                "chunk_index": chunk_index,
                                "page_start": page_num,
                                "page_end": page_num,
                                "char_start": char_offset,
                                "char_end": char_offset + len(chunk_text),
                            }
                        ))
                        chunk_index += 1
                        char_offset += len(chunk_text) - overlap
                    current_chunk = ""
                else:
                    current_chunk = page_text
                    current_page_start = page_num
                    current_page_end = page_num
        
        # Add final chunk
        if current_chunk:
            chunks.append((
                current_chunk,
                {
                    "chunk_index": chunk_index,
                    "page_start": current_page_start,
                    "page_end": current_page_end,
                    "char_start": char_offset,
                    "char_end": char_offset + len(current_chunk),
                }
            ))
        
        return chunks
    
    def _chunk_text_semantic(
        self,
        text: str,
        chunk_size: int,
        overlap: int,
        min_chunk_size: int
    ) -> List[Tuple[str, Dict]]:
        """Chunk text using semantic boundaries."""
        chunks = []
        chunk_index = 0
        current_pos = 0
        text_length = len(text)
        
        while current_pos < text_length:
            # Determine target end position
            target_end = min(current_pos + chunk_size, text_length)
            
            if target_end >= text_length:
                # Last chunk - take everything remaining
                chunk_text = text[current_pos:].strip()
                if chunk_text:
                    chunks.append((
                        chunk_text,
                        {
                            "chunk_index": chunk_index,
                            "char_start": current_pos,
                            "char_end": text_length,
                        }
                    ))
                break
            
            # Try to find semantic break point
            # 1. Try paragraph break (double newline)
            best_break = self._find_paragraph_break(text, current_pos, target_end)
            
            # 2. If no paragraph break, try sentence break
            if best_break == target_end:
                best_break = self._find_sentence_break(text, current_pos, target_end)
            
            # 3. If no sentence break, try clause break
            if best_break == target_end:
                best_break = self._find_clause_break(text, current_pos, target_end)
            
            # Ensure minimum chunk size
            if best_break - current_pos < min_chunk_size:
                # Extend to minimum size, but don't exceed chunk_size too much
                best_break = min(current_pos + min_chunk_size, text_length)
            
            # Extract chunk
            chunk_text = text[current_pos:best_break].strip()
            if chunk_text:
                chunks.append((
                    chunk_text,
                    {
                        "chunk_index": chunk_index,
                        "char_start": current_pos,
                        "char_end": best_break,
                    }
                ))
                chunk_index += 1
            
            # Move forward with overlap
            if overlap > 0:
                # Find overlap start (go back overlap amount, but at semantic boundary)
                overlap_start = max(current_pos, best_break - overlap)
                # Try to start overlap at sentence or paragraph boundary
                overlap_start = self._find_sentence_break(text, overlap_start, best_break)
                current_pos = overlap_start
            else:
                current_pos = best_break
        
        return chunks
    
    def _find_paragraph_break(self, text: str, start: int, end: int) -> int:
        """Find paragraph break (double newline) near end position."""
        # Look for double newline in the last 30% of chunk
        search_start = max(start, end - int((end - start) * 0.3))
        break_pos = text.rfind("\n\n", search_start, end)
        if break_pos > start:
            return break_pos + 2  # Include the newlines
        return end
    
    def _find_sentence_break(self, text: str, start: int, end: int) -> int:
        """Find sentence break near end position."""
        # Look for sentence ending in the last 20% of chunk
        search_start = max(start, end - int((end - start) * 0.2))
        search_text = text[search_start:end]
        
        matches = list(self.sentence_endings.finditer(search_text))
        if matches:
            # Use last sentence ending
            last_match = matches[-1]
            return search_start + last_match.end()
        
        return end
    
    def _find_clause_break(self, text: str, start: int, end: int) -> int:
        """Find clause break (comma, semicolon, colon) near end position."""
        # Look for clause separator in the last 10% of chunk
        search_start = max(start, end - int((end - start) * 0.1))
        search_text = text[search_start:end]
        
        matches = list(self.clause_separators.finditer(search_text))
        if matches:
            # Use last clause separator
            last_match = matches[-1]
            return search_start + last_match.end()
        
        return end
