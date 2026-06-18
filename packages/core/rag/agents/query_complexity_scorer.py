"""
Query Complexity Scorer

Classifies query complexity to skip expensive operations for simple queries.
Query rewriting is always handled upstream (no skip_rewrite flag).
"""

import re
from typing import Dict, Any
from enum import Enum


class QueryComplexity(str, Enum):
    """Query complexity levels."""

    SIMPLE = "simple"  # < 8 words, no operators - skip some expensive ops
    MEDIUM = "medium"  # 8-15 words or simple operators
    COMPLEX = "complex"  # > 15 words or complex operators


class QueryComplexityScorer:
    """
    Scores query complexity to determine which operations to skip.

    Simple queries (< 8 words, no operators):
    - Skip reranker (Cohere), confidence LLM evaluation, and query rewrite
    """

    def __init__(self):
        self.complex_operators = [
            r"\b(and|or|but|not|except|without)\b",
            r"\b(compare|versus|vs|difference|similar|different)\b",
            r"\b(explain|analyze|break down|elaborate|detail)\b",
            r"\b(how|why|what if|suppose|imagine)\b",
            r"\b(all|every|each|both|either|neither)\b",
        ]

    def score_complexity(self, query: str) -> Dict[str, Any]:
        if not query or not query.strip():
            return {
                "complexity": QueryComplexity.SIMPLE,
                "word_count": 0,
                "has_operators": False,
                "should_skip_rerank": True,
                "should_skip_confidence": True,
                "should_skip_rewrite": True,
            }

        words = query.split()
        word_count = len(words)
        query_lower = query.lower()
        has_operators = any(
            re.search(pattern, query_lower, re.IGNORECASE) for pattern in self.complex_operators
        )

        if word_count < 8 and not has_operators:
            complexity = QueryComplexity.SIMPLE
            should_skip_rerank = True
            should_skip_confidence = True
            should_skip_rewrite = True
        elif word_count < 15 and not has_operators:
            complexity = QueryComplexity.MEDIUM
            should_skip_rerank = False
            should_skip_confidence = False
            should_skip_rewrite = False
        else:
            complexity = QueryComplexity.COMPLEX
            should_skip_rerank = False
            should_skip_confidence = False
            should_skip_rewrite = False

        return {
            "complexity": complexity,
            "word_count": word_count,
            "has_operators": has_operators,
            "should_skip_rerank": should_skip_rerank,
            "should_skip_confidence": should_skip_confidence,
            "should_skip_rewrite": should_skip_rewrite,
        }
