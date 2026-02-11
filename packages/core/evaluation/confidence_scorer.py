"""
Confidence Scorer

Calculates confidence scores for RAG responses.
"""

from typing import Dict, List, Optional, Any
from enum import Enum


class ConfidenceLevel(Enum):
    """Confidence levels."""
    HIGH = "high"  # >= 0.7
    MEDIUM = "medium"  # 0.5 - 0.7
    LOW = "low"  # < 0.5


class ConfidenceScorer:
    """
    Calculates confidence scores for RAG responses.
    
    Factors:
    - Citation relevance and scores
    - Answer completeness
    - Query-answer alignment
    - Retrieval quality
    """
    
    def __init__(
        self,
        low_threshold: float = 0.5,
        high_threshold: float = 0.7
    ):
        """
        Initialize confidence scorer.
        
        Args:
            low_threshold: Threshold for low confidence (< this)
            high_threshold: Threshold for high confidence (>= this)
        """
        self.low_threshold = low_threshold
        self.high_threshold = high_threshold
    
    def calculate_confidence(
        self,
        query: str,
        answer: str,
        citations: List[Dict],
        retrieval_scores: Optional[List[float]] = None,
        answer_length: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Calculate confidence score for a response.
        
        Args:
            query: User query
            answer: Generated answer
            citations: List of citations
            retrieval_scores: Optional list of retrieval scores
            answer_length: Optional answer length
            
        Returns:
            Dict with:
            - confidence: float (0.0-1.0)
            - level: ConfidenceLevel
            - factors: Dict of contributing factors
            - flagged: bool (if low confidence)
        """
        factors = {}
        
        # Factor 1: Citation quality (0-0.4 weight)
        citation_score = self._score_citations(citations, retrieval_scores)
        factors["citations"] = citation_score
        
        # Factor 2: Answer completeness (0-0.3 weight)
        completeness_score = self._score_completeness(answer, answer_length)
        factors["completeness"] = completeness_score
        
        # Factor 3: Query-answer alignment (0-0.3 weight)
        alignment_score = self._score_alignment(query, answer)
        factors["alignment"] = alignment_score
        
        # Weighted confidence
        confidence = (
            citation_score * 0.4 +
            completeness_score * 0.3 +
            alignment_score * 0.3
        )
        
        # Determine level
        if confidence >= self.high_threshold:
            level = ConfidenceLevel.HIGH
        elif confidence >= self.low_threshold:
            level = ConfidenceLevel.MEDIUM
        else:
            level = ConfidenceLevel.LOW
        
        flagged = confidence < self.low_threshold
        
        return {
            "confidence": confidence,
            "level": level.value,
            "factors": factors,
            "flagged": flagged,
            "message": self._get_confidence_message(level, flagged)
        }
    
    def _score_citations(
        self,
        citations: List[Dict],
        retrieval_scores: Optional[List[float]] = None
    ) -> float:
        """Score based on citation quality."""
        if not citations:
            return 0.2  # Low score without citations
        
        # Count citations
        citation_count = len(citations)
        count_score = min(citation_count / 5, 1.0)  # 5+ citations = full score
        
        # Average citation score
        if retrieval_scores:
            avg_score = sum(retrieval_scores) / len(retrieval_scores)
        else:
            # Use scores from citations if available
            scores = [c.get("score", 0.5) for c in citations]
            avg_score = sum(scores) / len(scores) if scores else 0.5
        
        # Combined score
        return (count_score * 0.5 + avg_score * 0.5)
    
    def _score_completeness(
        self,
        answer: str,
        answer_length: Optional[int] = None
    ) -> float:
        """Score based on answer completeness."""
        length = answer_length or len(answer)
        
        if length < 20:
            return 0.2  # Very short answer
        elif length < 100:
            return 0.5  # Short answer
        elif length < 300:
            return 0.8  # Good length
        else:
            return 1.0  # Comprehensive answer
    
    def _score_alignment(
        self,
        query: str,
        answer: str
    ) -> float:
        """Score based on query-answer alignment."""
        # Simple keyword overlap
        query_words = set(query.lower().split())
        answer_words = set(answer.lower().split())
        
        if not query_words:
            return 0.5
        
        overlap = len(query_words.intersection(answer_words))
        overlap_ratio = overlap / len(query_words)
        
        return min(overlap_ratio * 1.2, 1.0)  # Slight boost for good overlap
    
    def _get_confidence_message(
        self,
        level: ConfidenceLevel,
        flagged: bool
    ) -> str:
        """Get human-readable confidence message."""
        if flagged:
            return "Low confidence response - may need review"
        elif level == ConfidenceLevel.HIGH:
            return "High confidence response"
        elif level == ConfidenceLevel.MEDIUM:
            return "Medium confidence response"
        else:
            return "Low confidence response"
