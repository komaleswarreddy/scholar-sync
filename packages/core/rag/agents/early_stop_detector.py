"""
Early Stop Detector

Detects when the response has fully answered the query and can stop early.
Prevents verbose, repetitive responses.
"""

import re
from typing import Dict, Any, Optional, List


class EarlyStopDetector:
    """
    Agent that detects when a response has fully answered the query.
    
    Strategies:
    - Detects answer completion signals
    - Identifies repetitive content
    - Checks if query is fully answered
    - Suggests stopping points
    """
    
    def __init__(
        self,
        enabled: bool = True,
        min_length: int = 200,  # Minimum response length before early stop (increased for completeness)
        repetition_threshold: float = 0.5  # 50% similarity = repetitive (increased threshold)
    ):
        """
        Initialize early stop detector.
        
        Args:
            enabled: Whether early stopping is enabled
            min_length: Minimum response length (characters) before stopping
            repetition_threshold: Similarity threshold for detecting repetition
        """
        self.enabled = enabled
        self.min_length = min_length
        self.repetition_threshold = repetition_threshold
        
        # Completion signals
        self.completion_signals = [
            r'\b(in conclusion|to summarize|in summary|to conclude)\b',
            r'\b(overall|in essence|essentially|basically)\b',
            r'\.{3,}',  # Multiple periods (trailing off)
            r'\?$',  # Ends with question (uncertainty)
        ]
        
        # Answer completion patterns
        self.answer_patterns = [
            r'\b(therefore|thus|hence|so|as a result)\b',
            r'\b(in summary|to sum up|in conclusion)\b',
            r'\.\s*$',  # Ends with period (complete thought)
        ]
    
    def should_stop(
        self,
        accumulated_text: str,
        query: str,
        last_chunk: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Determine if response should stop early.
        
        Args:
            accumulated_text: All text accumulated so far
            query: Original user query
            last_chunk: Last chunk received (for repetition detection)
            
        Returns:
            Dict with:
            - should_stop: bool
            - reason: str (reason for stopping)
            - confidence: float (0.0-1.0)
        """
        if not self.enabled:
            return {"should_stop": False, "reason": "disabled", "confidence": 0.0}
        
        # Don't stop if too short
        if len(accumulated_text) < self.min_length:
            return {"should_stop": False, "reason": "too_short", "confidence": 0.0}
        
        # Check for completion signals
        completion_score = self._check_completion_signals(accumulated_text)
        if completion_score > 0.7:
            return {
                "should_stop": True,
                "reason": "completion_signal",
                "confidence": completion_score
            }
        
        # Check if query is answered (be more conservative - require higher completeness)
        answer_completeness = self._check_answer_completeness(accumulated_text, query)
        if answer_completeness > 0.95 and len(accumulated_text) > 300:  # Require very high completeness and sufficient length
            return {
                "should_stop": True,
                "reason": "query_answered",
                "confidence": answer_completeness
            }
        
        # Check for repetition
        if last_chunk:
            repetition_score = self._check_repetition(accumulated_text, last_chunk)
            if repetition_score > self.repetition_threshold:
                return {
                    "should_stop": True,
                    "reason": "repetition",
                    "confidence": repetition_score
                }
        
        # Check for trailing off (incomplete sentences at end)
        if self._is_trailing_off(accumulated_text):
            return {
                "should_stop": True,
                "reason": "trailing_off",
                "confidence": 0.6
            }
        
        return {"should_stop": False, "reason": "continue", "confidence": 0.0}
    
    def _check_completion_signals(self, text: str) -> float:
        """Check for completion signals in text."""
        score = 0.0
        
        # Check last 200 characters for completion signals
        last_part = text[-200:] if len(text) > 200 else text
        
        for pattern in self.completion_signals:
            if re.search(pattern, last_part, re.IGNORECASE):
                score += 0.3
        
        # Check if ends with complete sentence
        if re.search(r'\.\s*$', text.strip()):
            score += 0.2
        
        return min(score, 1.0)
    
    def _check_answer_completeness(self, text: str, query: str) -> float:
        """Check if query has been fully answered."""
        # Extract keywords from query
        query_keywords = set(re.findall(r'\b\w{3,}\b', query.lower()))
        
        if not query_keywords:
            return 0.5  # Can't determine
        
        # Check if response contains query keywords
        text_lower = text.lower()
        matched_keywords = sum(1 for kw in query_keywords if kw in text_lower)
        keyword_coverage = matched_keywords / len(query_keywords) if query_keywords else 0
        
        # Check for answer patterns
        has_answer_pattern = any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in self.answer_patterns
        )
        
        # Combine scores
        completeness = (keyword_coverage * 0.6) + (0.4 if has_answer_pattern else 0)
        
        return min(completeness, 1.0)
    
    def _check_repetition(self, full_text: str, last_chunk: str) -> float:
        """Check if last chunk is repetitive of earlier content."""
        if len(last_chunk) < 20:  # Too short to compare
            return 0.0
        
        # Compare last chunk with earlier text
        earlier_text = full_text[:-len(last_chunk)] if len(full_text) > len(last_chunk) else ""
        
        if not earlier_text:
            return 0.0
        
        # Simple similarity: count common words
        last_words = set(re.findall(r'\b\w{3,}\b', last_chunk.lower()))
        earlier_words = set(re.findall(r'\b\w{3,}\b', earlier_text.lower()))
        
        if not last_words:
            return 0.0
        
        common_words = last_words.intersection(earlier_words)
        similarity = len(common_words) / len(last_words) if last_words else 0
        
        return similarity
    
    def _is_trailing_off(self, text: str) -> bool:
        """Check if text is trailing off (incomplete)."""
        # Check last 100 characters
        last_part = text[-100:] if len(text) > 100 else text
        
        # Ends with ellipsis
        if re.search(r'\.{3,}\s*$', last_part):
            return True
        
        # Ends with incomplete sentence (no period, question mark, or exclamation)
        if not re.search(r'[.!?]\s*$', text.strip()):
            # But has substantial content, might be trailing off
            if len(text) > 200:
                return True
        
        return False
    
    def find_stop_point(self, text: str) -> Optional[int]:
        """
        Find the best point to stop in the text.
        
        Returns:
            Character index where to stop, or None if shouldn't stop
        """
        stop_result = self.should_stop(text, "")
        
        if not stop_result["should_stop"]:
            return None
        
        # Find last complete sentence
        sentences = re.split(r'([.!?]+)', text)
        
        if len(sentences) >= 3:  # At least one complete sentence
            # Find last complete sentence
            last_complete = ""
            for i in range(len(sentences) - 1, -1, -1):
                if sentences[i].strip() and re.search(r'[.!?]', sentences[i]):
                    last_complete = "".join(sentences[:i+1])
                    break
            
            if last_complete:
                return len(last_complete.strip())
        
        return None
