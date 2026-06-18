"""
Intent Gate

Academic-only intent enforcement to block non-academic queries.
"""

import re
from typing import Dict, List, Optional, Any
from enum import Enum


class IntentCategory(Enum):
    """Intent categories."""
    ACADEMIC = "academic"
    GENERAL_QA = "general_qa"
    PERSONAL = "personal"
    ENTERTAINMENT = "entertainment"
    INAPPROPRIATE = "inappropriate"
    UNKNOWN = "unknown"


class IntentGate:
    """
    Enforces academic-only intent filtering.
    
    Blocks non-academic queries and redirects to academic topics.
    """
    
    def __init__(
        self,
        strict_mode: bool = True,
        academic_threshold: float = 0.5
    ):
        """
        Initialize intent gate.
        
        Args:
            strict_mode: Strictly enforce academic-only (default: True)
            academic_threshold: Minimum confidence for academic intent
        """
        self.strict_mode = strict_mode
        self.academic_threshold = academic_threshold
        
        # Academic keywords and patterns
        self.academic_patterns = [
            r'\b(study|studying|learn|learning|teach|teaching|education|educational)\b',
            r'\b(homework|assignment|project|essay|paper|research)\b',
            r'\b(explain|define|what\s+is|what\s+are|what\s+role|how\s+does|why\s+does)\b',
            r'\b(subject|course|class|lesson|chapter|textbook)\b',
            r'\b(math|science|history|literature|english|biology|chemistry|physics)\b',
            r'\b(question|problem|solution|answer|help\s+with|understand)\b',
            r'\b(photosynthesis|calvin|chlorophyll|mitochondria|reactant|equation)\b',
        ]
        
        # Non-academic patterns (to detect and block)
        self.non_academic_patterns = {
            IntentCategory.PERSONAL: [
                r'\b(personal|private|my\s+life|about\s+me)\b',
                r'\b(relationship|dating|friend|family)\b',
            ],
            IntentCategory.ENTERTAINMENT: [
                r'\b(game|gaming|video\s+game|fun|entertainment|movie|music|song)\b',
                r'\b(joke|funny|meme|comedy)\b',
            ],
            IntentCategory.INAPPROPRIATE: [
                r'\b(inappropriate|inappropriate\s+content)\b',
            ],
        }
    
    def classify_intent(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Classify query intent.
        
        Args:
            query: User query
            context: Optional context
            
        Returns:
            Dict with:
            - category: IntentCategory
            - confidence: float
            - is_academic: bool
            - should_block: bool
            - message: str (if blocked)
        """
        if not query or not query.strip():
            return {
                "category": IntentCategory.UNKNOWN.value,
                "confidence": 0.0,
                "is_academic": False,
                "should_block": True,
                "message": "Empty query"
            }
        
        query_lower = query.lower()
        
        # Check for academic patterns
        academic_matches = sum(
            1 for pattern in self.academic_patterns
            if re.search(pattern, query_lower, re.IGNORECASE)
        )
        academic_confidence = min(academic_matches / max(len(query.split()), 1), 1.0)
        
        # Check for non-academic patterns
        detected_non_academic = []
        for category, patterns in self.non_academic_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    detected_non_academic.append(category.value)
        
        # Determine category
        if academic_confidence >= self.academic_threshold:
            category = IntentCategory.ACADEMIC
            is_academic = True
        elif detected_non_academic:
            category = IntentCategory(detected_non_academic[0])
            is_academic = False
        else:
            category = IntentCategory.GENERAL_QA
            is_academic = False  # Default to non-academic if unclear
        
        # Determine if should block
        should_block = (
            self.strict_mode and
            not is_academic and
            category != IntentCategory.GENERAL_QA
        )
        
        message = None
        if should_block:
            if category == IntentCategory.PERSONAL:
                message = "I focus on academic questions. What subject are you studying?"
            elif category == IntentCategory.ENTERTAINMENT:
                message = "I'm here to help with your studies. What academic topic can I assist with?"
            elif category == IntentCategory.INAPPROPRIATE:
                message = "I can't help with that. Let's focus on your schoolwork!"
            else:
                message = "I specialize in academic topics. What would you like to learn about?"
        
        return {
            "category": category.value,
            "confidence": academic_confidence if is_academic else (1.0 - academic_confidence),
            "is_academic": is_academic,
            "should_block": should_block,
            "message": message,
            "detected_non_academic": detected_non_academic
        }
    
    def check_and_block(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Check query and block if non-academic.
        
        Args:
            query: User query
            context: Optional context
            
        Returns:
            Dict with blocking decision
        """
        intent_result = self.classify_intent(query, context)
        
        if intent_result["should_block"]:
            return {
                "allowed": False,
                "blocked": True,
                "reason": "non_academic",
                "intent_category": intent_result["category"],
                "message": intent_result["message"]
            }
        
        return {
            "allowed": True,
            "blocked": False,
            "intent_category": intent_result["category"],
            "is_academic": intent_result["is_academic"]
        }
