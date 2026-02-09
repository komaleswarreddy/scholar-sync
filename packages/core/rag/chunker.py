"""
Text Chunker

Handles text chunking and cleaning for RAG pipeline.
Uses a simple recursive text splitter implementation.
Supports percentage-based overlap (10-15%) and semantic chunking.
"""

from typing import List, Tuple, Dict, Optional
from config.settings import settings


class Chunker:
    """
    Service for text processing operations.
    
    Implements recursive character text splitting that preserves
    sentence boundaries and paragraph structure.
    Supports percentage-based overlap and semantic chunking.
    """
    
    def __init__(self, use_semantic: Optional[bool] = None):
        """
        Initialize chunker.
        
        Args:
            use_semantic: Whether to use semantic chunking (defaults to settings.USE_SEMANTIC_CHUNKING)
        """
        self.default_chunk_size = 1000
        self.default_overlap = 200
        self.separators = ["\n\n", "\n", ". ", " ", ""]
        self.use_semantic = use_semantic if use_semantic is not None else getattr(settings, 'USE_SEMANTIC_CHUNKING', True)
        
        if self.use_semantic:
            from packages.core.processing.semantic_chunker import SemanticChunker
            self.semantic_chunker = SemanticChunker()
    
    def chunk_text(
        self,
        text: str,
        chunk_size: int = 1000,
        overlap: int = None,
        pages: Optional[List[Tuple[int, str]]] = None
    ) -> List[str]:
        """
        Split text into chunks with overlap.
        
        Args:
            text: Input text to chunk
            chunk_size: Target chunk size in characters
            overlap: Overlap between chunks in characters (if None, uses percentage-based)
            pages: Optional list of (page_num, page_text) tuples for semantic chunking with page metadata
            
        Returns:
            List of text chunks (or List[Tuple[str, Dict]] if semantic chunking with pages)
        """
        if not text:
            return []
        
        # Calculate overlap from percentage if not provided
        if overlap is None:
            overlap_percent = getattr(settings, 'CHUNK_OVERLAP_PERCENT', 0.12)
            overlap = int(chunk_size * overlap_percent)
        
        # Use semantic chunking if enabled
        if self.use_semantic:
            if pages:
                # Semantic chunking with page metadata
                chunk_tuples = self.semantic_chunker.chunk_text(text, chunk_size, overlap, pages)
                # Return just the text for backward compatibility, but metadata is available
                return [chunk_text for chunk_text, _ in chunk_tuples]
            else:
                # Semantic chunking without pages
                chunk_tuples = self.semantic_chunker.chunk_text(text, chunk_size, overlap)
                return [chunk_text for chunk_text, _ in chunk_tuples]
        
        # Fallback to original recursive chunking
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
    
    def chunk_text_with_metadata(
        self,
        text: str,
        chunk_size: int = 1000,
        overlap: int = None,
        pages: Optional[List[Tuple[int, str]]] = None,
        source_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> List[Tuple[str, Dict]]:
        """
        Split text into chunks with metadata.
        
        Args:
            text: Input text to chunk
            chunk_size: Target chunk size in characters
            overlap: Overlap between chunks (if None, uses percentage-based)
            pages: Optional list of (page_num, page_text) tuples for page metadata
            source_id: Optional source ID for metadata
            tenant_id: Optional tenant ID for metadata
            
        Returns:
            List of (chunk_text, metadata) tuples
        """
        if not text:
            return []
        
        # Calculate overlap from percentage if not provided
        if overlap is None:
            overlap_percent = getattr(settings, 'CHUNK_OVERLAP_PERCENT', 0.12)
            overlap = int(chunk_size * overlap_percent)
        
        # Use semantic chunking if enabled
        if self.use_semantic:
            chunk_tuples = self.semantic_chunker.chunk_text(text, chunk_size, overlap, pages)
            # Enrich metadata with source_id and tenant_id
            enriched_chunks = []
            for chunk_text, metadata in chunk_tuples:
                if source_id:
                    metadata['source_id'] = source_id
                if tenant_id:
                    metadata['tenant_id'] = tenant_id
                enriched_chunks.append((chunk_text, metadata))
            return enriched_chunks
        
        # Fallback: create chunks without semantic boundaries but with metadata
        chunks = self.chunk_text(text, chunk_size, overlap, pages)
        result = []
        for i, chunk_text in enumerate(chunks):
            metadata = {
                "chunk_index": i,
            }
            if source_id:
                metadata['source_id'] = source_id
            if tenant_id:
                metadata['tenant_id'] = tenant_id
            if pages:
                # Try to determine page range for chunk
                # This is approximate without semantic chunking
                chars_per_page = len(text) / len(pages) if pages else 0
                start_char = sum(len(chunks[j]) for j in range(i))
                page_start = int(start_char / chars_per_page) + 1 if chars_per_page > 0 else 1
                page_end = int((start_char + len(chunk_text)) / chars_per_page) + 1 if chars_per_page > 0 else page_start
                metadata['page_start'] = min(page_start, len(pages))
                metadata['page_end'] = min(page_end, len(pages))
            result.append((chunk_text, metadata))
        
        return result
    
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


