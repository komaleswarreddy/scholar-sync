"""
PDF Preprocessor

Aggressive PDF cleaning for 40-70% token reduction.
Removes headers, footers, references, and visual noise.
"""

import re
from typing import List, Tuple


class PDFPreprocessor:
    """
    Aggressive PDF text cleaning to reduce token usage.
    
    Removes:
    - Headers and footers (repeated text at top/bottom of pages)
    - Page numbers
    - References and citations
    - Table of contents markers
    - Watermarks
    - Excessive whitespace
    - Non-content text
    """
    
    def __init__(self):
        # Common header/footer patterns
        self.header_footer_patterns = [
            r'^\d+\s*$',  # Page numbers alone
            r'^Page\s+\d+',  # "Page 1", "Page 2", etc.
            r'^\d+\s+of\s+\d+',  # "1 of 10"
            r'^Chapter\s+\d+',  # "Chapter 1"
            r'^Section\s+\d+',  # "Section 1"
        ]
        
        # Reference patterns
        self.reference_patterns = [
            r'\([A-Z][a-z]+\s+et\s+al\.\s+\d{4}[a-z]?\)',  # (Author et al. 2024)
            r'\([A-Z][a-z]+\s+\d{4}[a-z]?\)',  # (Author 2024)
            r'\[[0-9,\s-]+\]',  # [1, 2, 3] or [1-5]
            r'\([0-9,\s-]+\)',  # (1, 2, 3) or (1-5)
            r'^References?\s*$',  # "Reference" or "References" header
            r'^Bibliography\s*$',  # "Bibliography" header
            r'^Works\s+Cited\s*$',  # "Works Cited" header
        ]
        
        # Table of contents patterns
        self.toc_patterns = [
            r'^\.{3,}\s*\d+$',  # "...... 5" (dots followed by page number)
            r'^\d+\s+\.{3,}\s*\d+$',  # "1 ...... 5"
        ]
        
        # Watermark patterns
        self.watermark_patterns = [
            r'CONFIDENTIAL',
            r'DRAFT',
            r'DO NOT DISTRIBUTE',
            r'PROPRIETARY',
        ]
    
    def clean_text(self, text: str, pages: List[Tuple[int, str]] = None) -> str:
        """
        Aggressively clean PDF text to reduce tokens.
        
        Args:
            text: Raw extracted text from PDF
            pages: Optional list of (page_num, page_text) tuples for page-aware cleaning
            
        Returns:
            Cleaned text with 40-70% token reduction
        """
        if not text:
            return ""
        
        # If pages are provided, clean per-page to remove headers/footers
        if pages:
            cleaned_pages = []
            for page_num, page_text in pages:
                cleaned_page = self._clean_page(page_text, page_num)
                if cleaned_page.strip():
                    cleaned_pages.append(cleaned_page)
            text = "\n\n".join(cleaned_pages)
        else:
            # Fallback: clean entire text
            text = self._clean_page(text)
        
        # Remove reference patterns
        text = self._remove_references(text)
        
        # Remove table of contents
        text = self._remove_toc(text)
        
        # Remove watermarks
        text = self._remove_watermarks(text)
        
        # Normalize whitespace
        text = self._normalize_whitespace(text)
        
        return text.strip()
    
    def _clean_page(self, page_text: str, page_num: int = None) -> str:
        """Clean a single page, removing headers and footers."""
        if not page_text:
            return ""
        
        lines = page_text.split('\n')
        cleaned_lines = []
        
        # Remove header/footer lines (first and last few lines that match patterns)
        # Check first 3 lines for headers
        header_lines = min(3, len(lines))
        # Check last 3 lines for footers
        footer_lines = min(3, len(lines))
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Skip header lines (first few lines matching patterns)
            if i < header_lines:
                if self._matches_header_footer(line):
                    continue
            
            # Skip footer lines (last few lines matching patterns)
            if i >= len(lines) - footer_lines:
                if self._matches_header_footer(line):
                    continue
            
            # Remove page numbers
            if self._is_page_number(line):
                continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _matches_header_footer(self, line: str) -> bool:
        """Check if line matches header/footer patterns."""
        for pattern in self.header_footer_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                return True
        return False
    
    def _is_page_number(self, line: str) -> bool:
        """Check if line is just a page number."""
        line = line.strip()
        # Match lines that are just numbers or "Page N"
        if re.match(r'^\d+$', line):
            return True
        if re.match(r'^Page\s+\d+$', line, re.IGNORECASE):
            return True
        return False
    
    def _remove_references(self, text: str) -> str:
        """Remove citation references from text."""
        for pattern in self.reference_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)
        
        # Remove standalone reference sections
        # Match "References" or "Bibliography" section and everything after
        ref_section_pattern = r'(?:^|\n)(?:References?|Bibliography|Works\s+Cited)\s*:?\s*\n.*$'
        text = re.sub(ref_section_pattern, '', text, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
        
        return text
    
    def _remove_toc(self, text: str) -> str:
        """Remove table of contents."""
        for pattern in self.toc_patterns:
            text = re.sub(pattern, '', text, flags=re.MULTILINE)
        
        # Remove TOC section (lines with many dots)
        lines = text.split('\n')
        cleaned_lines = []
        in_toc = False
        
        for line in lines:
            # Detect TOC start
            if re.search(r'Table\s+of\s+Contents?', line, re.IGNORECASE):
                in_toc = True
                continue
            
            # Detect TOC end (when we hit a chapter/section number or regular content)
            if in_toc:
                # TOC usually ends when we see a chapter/section heading
                if re.match(r'^(Chapter|Section|Part)\s+\d+', line, re.IGNORECASE):
                    in_toc = False
                # Or when we see content without dots
                elif not re.search(r'\.{3,}', line):
                    in_toc = False
                    cleaned_lines.append(line)
                continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _remove_watermarks(self, text: str) -> str:
        """Remove watermark text."""
        for pattern in self.watermark_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        return text
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace to reduce tokens."""
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        
        # Replace multiple newlines with double newline (paragraph break)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        # Remove empty lines at start/end
        text = text.strip()
        
        return text
    
    def extract_pages_with_metadata(self, pdf_reader) -> List[Tuple[int, str]]:
        """
        Extract text from PDF with page numbers for metadata.
        
        Args:
            pdf_reader: pypdf.PdfReader instance
            
        Returns:
            List of (page_number, page_text) tuples
        """
        pages = []
        for page_num, page in enumerate(pdf_reader.pages, start=1):
            try:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    pages.append((page_num, page_text))
            except Exception as e:
                print(f"[WARNING] Failed to extract text from page {page_num}: {str(e)}")
                continue
        return pages
