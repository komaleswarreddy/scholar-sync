"""
Query Complexity Scorer

Classifies query complexity to skip expensive operations for simple queries.
Simple queries don't need query rewriting, reranking, or confidence evaluation.
"""

import re
from typing import Dict, Any
from enum import Enum


class QueryComplexity(str, Enum):
    """Query complexity levels."""
    SIMPLE = "simple"  # < 8 words, no operators - skip expensive ops
    MEDIUM = "medium"  # 8-15 words or simple operators
    COMPLEX = "complex"  # > 15 words or complex operators


class QueryComplexityScorer:
    """
    Scores query complexity to determine which operations to skip.
    
    Simple queries (< 8 words, no operators):
    - Skip query rewrite
    - Skip reranker
    - Skip confidence LLM evaluation
    """
    
    def __init__(self):
        """Initialize query complexity scorer."""
        # Operators that indicate complex queries
        self.complex_operators = [
            r'\b(and|or|but|not|except|without)\b',  # Logical operators
            r'\b(compare|versus|vs|difference|similar|different)\b',  # Comparison
            r'\b(explain|analyze|break down|elaborate|detail)\b',  # Analysis
            r'\b(how|why|what if|suppose|imagine)\b',  # Complex questions
            r'\b(all|every|each|both|either|neither)\b',  # Quantifiers
        ]
    
    def score_complexity(self, query: str) -> Dict[str, Any]:
        """
        Score query complexity.
        
        Args:
            query: User query text
            
        Returns:
            Dict with:
            - complexity: QueryComplexity enum
            - word_count: Number of words
            - has_operators: Whether query contains complex operators
            - should_skip_rewrite: Whether to skip query rewriting
            - should_skip_rerank: Whether to skip reranking
            - should_skip_confidence: Whether to skip confidence evaluation
        """
        if not query or not query.strip():
            return {
                "complexity": QueryComplexity.SIMPLE,
                "word_count": 0,
                "has_operators": False,
                "should_skip_rewrite": True,
                "should_skip_rerank": True,
                "should_skip_confidence": True,
            }
        
        # Count words
        words = query.split()
        word_count = len(words)
        
        # Check for complex operators
        query_lower = query.lower()
        has_operators = any(
            re.search(pattern, query_lower, re.IGNORECASE)
            for pattern in self.complex_operators
        )
        
        # Determine complexity
        if word_count < 8 and not has_operators:
            complexity = QueryComplexity.SIMPLE
            should_skip_rewrite = True
            should_skip_rerank = True
            should_skip_confidence = True
        elif word_count < 15 and not has_operators:
            complexity = QueryComplexity.MEDIUM
            should_skip_rewrite = False
            should_skip_rerank = False
            should_skip_confidence = False
        else:
            complexity = QueryComplexity.COMPLEX
            should_skip_rewrite = False
            should_skip_rerank = False
            should_skip_confidence = False
        
        return {
            "complexity": complexity,
            "word_count": word_count,
            "has_operators": has_operators,
            "should_skip_rewrite": should_skip_rewrite,
            "should_skip_rerank": should_skip_rerank,
            "should_skip_confidence": should_skip_confidence,
        }
