"""
Output Length Limiter

Enforces maximum output length limits to prevent verbose responses.
"""

import re
from typing import Dict, Any, Optional


class OutputLengthLimiter:
    """
    Agent that enforces output length limits.
    
    Strategies:
    - Truncates at sentence boundaries
    - Enforces token/character limits
    - Adds truncation indicators
    - Prevents excessive verbosity
    """
    
    def __init__(
        self,
        max_tokens: Optional[int] = None,
        max_characters: Optional[int] = None,
        max_sentences: Optional[int] = None,
        hard_limit: bool = True
    ):
        """
        Initialize output length limiter.
        
        Args:
            max_tokens: Maximum tokens (approximate, 1 token ≈ 4 characters)
            max_characters: Maximum characters
            max_sentences: Maximum sentences
            hard_limit: If True, strictly enforces limit; if False, warns only
        """
        self.max_tokens = max_tokens
        self.max_characters = max_characters
        self.max_sentences = max_sentences
        self.hard_limit = hard_limit
        
        # Convert tokens to characters if needed (rough estimate)
        if max_tokens and not max_characters:
            self.max_characters = max_tokens * 4
    
    def limit_output(
        self,
        text: str,
        add_truncation_note: bool = True
    ) -> Dict[str, Any]:
        """
        Limit output to specified constraints.
        
        Args:
            text: Original text
            add_truncation_note: Whether to add note if truncated
            
        Returns:
            Dict with:
            - text: Limited text
            - was_truncated: bool
            - original_length: int
            - new_length: int
            - reason: str
        """
        original_length = len(text)
        original_sentences = len(self._split_sentences(text))
        
        limited_text = text
        was_truncated = False
        reason = None
        
        # Check character limit
        if self.max_characters and len(text) > self.max_characters:
            limited_text = self._truncate_at_sentence(text, self.max_characters)
            was_truncated = True
            reason = f"exceeded_char_limit_{self.max_characters}"
        
        # Check sentence limit
        if self.max_sentences:
            sentences = self._split_sentences(limited_text)
            if len(sentences) > self.max_sentences:
                limited_text = " ".join(sentences[:self.max_sentences])
                was_truncated = True
                reason = f"exceeded_sentence_limit_{self.max_sentences}"
        
        # Add truncation note if needed
        if was_truncated and add_truncation_note:
            limited_text = self._add_truncation_note(limited_text)
        
        return {
            "text": limited_text,
            "was_truncated": was_truncated,
            "original_length": original_length,
            "new_length": len(limited_text),
            "original_sentences": original_sentences,
            "new_sentences": len(self._split_sentences(limited_text)),
            "reason": reason
        }
    
    def _truncate_at_sentence(self, text: str, max_chars: int) -> str:
        """Truncate at sentence boundary near max_chars."""
        if len(text) <= max_chars:
            return text
        
        # Find last complete sentence before limit
        truncated = text[:max_chars]
        
        # Find last sentence boundary
        last_period = truncated.rfind('.')
        last_question = truncated.rfind('?')
        last_exclamation = truncated.rfind('!')
        
        last_boundary = max(last_period, last_question, last_exclamation)
        
        if last_boundary > max_chars * 0.7:  # If boundary is reasonably close
            return text[:last_boundary + 1].strip()
        else:
            # No good boundary, truncate at word boundary
            last_space = truncated.rfind(' ')
            if last_space > max_chars * 0.8:
                return text[:last_space].strip() + "..."
            else:
                return truncated.strip() + "..."
    
    def _split_sentences(self, text: str) -> list:
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
    
    def _add_truncation_note(self, text: str) -> str:
        """Add note indicating truncation."""
        note = "\n\n*(Response truncated for conciseness. See source material for full details.)*"
        
        # Don't add if already ends with similar note
        if not re.search(r'truncat|abbreviated|shortened', text[-100:], re.IGNORECASE):
            return text + note
        
        return text
    
    def check_length(self, text: str) -> Dict[str, Any]:
        """
        Check if text exceeds limits (without truncating).
        
        Returns:
            Dict with length info and warnings
        """
        char_count = len(text)
        sentence_count = len(self._split_sentences(text))
        token_estimate = char_count // 4  # Rough estimate
        
        warnings = []
        exceeds_limits = False
        
        if self.max_characters and char_count > self.max_characters:
            warnings.append(f"Exceeds character limit: {char_count} > {self.max_characters}")
            exceeds_limits = True
        
        if self.max_tokens and token_estimate > self.max_tokens:
            warnings.append(f"Exceeds token limit: ~{token_estimate} > {self.max_tokens}")
            exceeds_limits = True
        
        if self.max_sentences and sentence_count > self.max_sentences:
            warnings.append(f"Exceeds sentence limit: {sentence_count} > {self.max_sentences}")
            exceeds_limits = True
        
        return {
            "char_count": char_count,
            "sentence_count": sentence_count,
            "token_estimate": token_estimate,
            "exceeds_limits": exceeds_limits,
            "warnings": warnings
        }
