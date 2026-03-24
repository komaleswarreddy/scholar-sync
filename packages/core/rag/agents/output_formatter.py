"""
Output Formatter

Forces structured output format for consistent responses.
Ensures all answers follow a consistent format.
"""

import re
from typing import Dict, Any, Optional
from enum import Enum


class OutputFormat(str, Enum):
    """Output format types."""
    BULLET_POINTS = "bullet_points"
    NUMBERED_LIST = "numbered_list"
    PARAGRAPH = "paragraph"
    STRUCTURED = "structured"  # Mix of headings and lists


class OutputFormatter:
    """
    Agent that formats responses into consistent structures.
    
    Strategies:
    - Converts to bullet points
    - Adds headings and structure
    - Ensures consistent formatting
    - Applies markdown formatting
    """
    
    def __init__(
        self,
        default_format: OutputFormat = OutputFormat.BULLET_POINTS,
        use_headings: bool = True,
        max_items: Optional[int] = None
    ):
        """
        Initialize output formatter.
        
        Args:
            default_format: Default format to use
            use_headings: Whether to add section headings
            max_items: Maximum items in lists (None = no limit)
        """
        self.default_format = default_format
        self.use_headings = use_headings
        self.max_items = max_items
    
    def format_response(
        self,
        response_text: str,
        query: str,
        format_type: Optional[OutputFormat] = None
    ) -> str:
        """
        Format response into structured output.
        
        Args:
            response_text: Raw response text
            query: Original user query
            format_type: Format to use (defaults to self.default_format)
            
        Returns:
            Formatted response text
        """
        format_type = format_type or self.default_format
        
        # Clean up response
        cleaned = self._clean_text(response_text)
        
        if format_type == OutputFormat.BULLET_POINTS:
            return self._format_as_bullets(cleaned, query)
        elif format_type == OutputFormat.NUMBERED_LIST:
            return self._format_as_numbered(cleaned, query)
        elif format_type == OutputFormat.STRUCTURED:
            return self._format_as_structured(cleaned, query)
        else:
            return self._format_as_paragraph(cleaned, query)
    
    def _format_as_bullets(self, text: str, query: str) -> str:
        """Format as bullet points."""
        # Extract main answer
        sentences = self._split_into_sentences(text)
        
        if not sentences:
            return text
        
        # First sentence is usually the direct answer
        first_sentence = sentences[0]
        
        # Remaining sentences become bullet points
        bullet_points = []
        
        # Check if already in bullet format
        if re.search(r'^[\-\*\+]\s+', text, re.MULTILINE):
            # Already formatted, just clean up
            return text
        
        # Convert to bullets
        for i, sentence in enumerate(sentences):
            if i == 0:
                # Keep first sentence as intro
                bullet_points.append(first_sentence)
                if len(sentences) > 1:
                    bullet_points.append("")  # Blank line
            else:
                # Convert to bullet
                cleaned = sentence.strip()
                if cleaned and not cleaned.startswith('-') and not cleaned.startswith('*'):
                    bullet_points.append(f"- {cleaned}")
                else:
                    bullet_points.append(cleaned)
        
        # Limit items if specified
        if self.max_items and len(bullet_points) > self.max_items + 1:  # +1 for intro
            bullet_points = bullet_points[:self.max_items + 1]
            bullet_points.append("\n*(Additional details available in source material)*")
        
        return "\n".join(bullet_points)
    
    def _format_as_numbered(self, text: str, query: str) -> str:
        """Format as numbered list."""
        sentences = self._split_into_sentences(text)
        
        if not sentences:
            return text
        
        first_sentence = sentences[0]
        numbered_items = [first_sentence, ""]
        
        for i, sentence in enumerate(sentences[1:], 1):
            cleaned = sentence.strip()
            if cleaned and not re.match(r'^\d+\.', cleaned):
                numbered_items.append(f"{i}. {cleaned}")
            else:
                numbered_items.append(cleaned)
        
        if self.max_items and len(numbered_items) > self.max_items + 1:
            numbered_items = numbered_items[:self.max_items + 1]
        
        return "\n".join(numbered_items)
    
    def _format_as_structured(self, text: str, query: str) -> str:
        """Format with headings and structure."""
        sentences = self._split_into_sentences(text)
        
        if not sentences:
            return text
        
        # Extract key concepts from query for heading
        query_keywords = self._extract_keywords(query)
        main_heading = query_keywords[0] if query_keywords else "Answer"
        
        formatted = [f"## {main_heading.title()}", ""]
        
        # First sentence as summary
        formatted.append(f"**{sentences[0]}**")
        formatted.append("")
        
        # Remaining as bullet points under subsections
        if len(sentences) > 1:
            formatted.append("### Key Points")
            formatted.append("")
            
            for sentence in sentences[1:]:
                cleaned = sentence.strip()
                if cleaned:
                    formatted.append(f"- {cleaned}")
        
        return "\n".join(formatted)
    
    def _format_as_paragraph(self, text: str, query: str) -> str:
        """Format as paragraph (minimal changes)."""
        # Just ensure proper spacing
        return re.sub(r'\n{3,}', '\n\n', text)
    
    def _clean_text(self, text: str) -> str:
        """Clean up text formatting without destroying Markdown (headings, lists, blank lines)."""
        text = (text or "").strip()
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Collapse spaces/tabs within each line only — newlines must survive for ReactMarkdown UI
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
        text = "\n".join(lines)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
    
    def _split_into_sentences(self, text: str) -> list:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r'([.!?]+(?:\s|$))', text)
        result = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                result.append(sentences[i] + sentences[i + 1])
            else:
                result.append(sentences[i])
        return [s.strip() for s in result if s.strip()]
    
    def _extract_keywords(self, text: str) -> list:
        """Extract keywords from text."""
        # Remove common stop words
        stop_words = {'what', 'is', 'are', 'the', 'a', 'an', 'how', 'why', 'when', 'where', 'who'}
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        return keywords[:3]  # Top 3 keywords
