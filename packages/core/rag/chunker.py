"""
Text Chunker

Handles text chunking and cleaning for RAG pipeline.
Uses a simple recursive text splitter implementation.
"""

from typing import List


class Chunker:
    """
    Service for text processing operations.
    
    Implements recursive character text splitting that preserves
    sentence boundaries and paragraph structure.
    """
    
    def __init__(self):
        self.default_chunk_size = 1000
        self.default_overlap = 200
        self.separators = ["\n\n", "\n", ". ", " ", ""]
    
    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        Split text into chunks with overlap.
        
        Args:
            text: Input text to chunk
            chunk_size: Target chunk size in characters
            overlap: Overlap between chunks in characters
            
        Returns:
            List of text chunks
        """
        if not text:
            return []
        
        chunks = []
        current_pos = 0
        text_length = len(text)
        
        while current_pos < text_length:
            # Determine end position for this chunk
            end_pos = min(current_pos + chunk_size, text_length)
            
            # If not at the end, try to break at a separator
            if end_pos < text_length:
                # Try to find a good break point
                best_break = end_pos
                for separator in self.separators:
                    # Look backwards for separator
                    search_start = max(current_pos, end_pos - chunk_size // 2)
                    break_pos = text.rfind(separator, search_start, end_pos)
                    if break_pos > search_start:
                        best_break = break_pos + len(separator)
                        break
                
                end_pos = best_break
            
            # Extract chunk
            chunk = text[current_pos:end_pos].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move position forward with overlap
            current_pos = max(current_pos + 1, end_pos - overlap)
        
        return chunks
    
    def clean_text(self, text: str) -> str:
        """
        Clean text by removing headers, footers, and extra whitespace.
        
        Args:
            text: Raw text to clean
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        lines = text.split("\n")
        cleaned_lines = [line.strip() for line in lines if line.strip()]
        return "\n".join(cleaned_lines)


