"""
Safety Filter

Input and output moderation for child-safe content.
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum


class SafetyCategory(Enum):
    """Safety categories for content moderation."""
    HARASSMENT = "harassment"
    HATE_SPEECH = "hate_speech"
    SEXUAL = "sexual"
    VIOLENCE = "violence"
    SELF_HARM = "self_harm"
    DANGEROUS = "dangerous"
    ILLEGAL = "illegal"
    INNAPPROPRIATE = "inappropriate"


class SafetyFilter:
    """
    Filters input and output for safety compliance.
    
    Ensures child-safe outputs and blocks inappropriate content.
    """
    
    def __init__(
        self,
        strict_mode: bool = True,
        block_threshold: float = 0.7
    ):
        """
        Initialize safety filter.
        
        Args:
            strict_mode: Enable strict filtering (default: True)
            block_threshold: Confidence threshold for blocking (0.0-1.0)
        """
        self.strict_mode = strict_mode
        self.block_threshold = block_threshold
        
        # Blocked patterns (basic keyword-based filtering)
        self.blocked_patterns = {
            SafetyCategory.HARASSMENT: [
                r'\b(kill|murder|suicide|harm|hurt)\b',
                r'\b(die|death|dead)\b',
            ],
            SafetyCategory.SEXUAL: [
                r'\b(sex|sexual|porn|nude|naked)\b',
            ],
            SafetyCategory.VIOLENCE: [
                r'\b(violence|violent|attack|fight|weapon|gun|knife)\b',
            ],
            SafetyCategory.ILLEGAL: [
                r'\b(drug|drugs|cocaine|heroin|marijuana)\b',
                r'\b(steal|rob|theft|illegal)\b',
            ],
            SafetyCategory.INNAPPROPRIATE: [
                r'\b(curse|swear|profanity)\b',
            ],
        }
        
        # Allowed academic contexts (exceptions for educational content)
        self.academic_exceptions = [
            r'\b(history|historical|literature|novel|book|study|research)\b',
            r'\b(medical|health|biology|science|education)\b',
        ]
    
    def check_input(
        self,
        text: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check input text for safety violations.
        
        Args:
            text: Input text to check
            context: Optional context (e.g., "academic", "medical")
            
        Returns:
            Dict with:
            - safe: bool
            - blocked: bool
            - categories: List of detected categories
            - confidence: float
            - message: str (if blocked)
        """
        if not text or not text.strip():
            return {
                "safe": True,
                "blocked": False,
                "categories": [],
                "confidence": 0.0,
                "message": None
            }
        
        text_lower = text.lower()
        detected_categories = []
        max_confidence = 0.0
        
        # Check each category
        for category, patterns in self.blocked_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                if matches:
                    # Calculate confidence (simple: number of matches / text length)
                    confidence = min(len(matches) / max(len(text.split()), 1), 1.0)
                    
                    # Check if in academic context (exception)
                    is_academic = False
                    if context and "academic" in context.lower():
                        for exception in self.academic_exceptions:
                            if re.search(exception, text_lower):
                                is_academic = True
                                break
                    
                    if not is_academic:
                        detected_categories.append(category.value)
                        max_confidence = max(max_confidence, confidence)
        
        # Determine if should block
        should_block = (
            len(detected_categories) > 0 and
            max_confidence >= self.block_threshold
        )
        
        if should_block:
            return {
                "safe": False,
                "blocked": True,
                "categories": detected_categories,
                "confidence": max_confidence,
                "message": f"Content contains inappropriate material: {', '.join(detected_categories)}"
            }
        
        return {
            "safe": True,
            "blocked": False,
            "categories": detected_categories if detected_categories else [],
            "confidence": max_confidence,
            "message": None
        }
    
    def check_output(
        self,
        text: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check output text for safety violations.
        
        Args:
            text: Output text to check
            context: Optional context
            
        Returns:
            Dict with safety check results
        """
        # Same logic as input check, but stricter for outputs
        result = self.check_input(text, context)
        
        # For outputs, be even more strict
        if self.strict_mode and result["categories"]:
            result["blocked"] = True
            result["safe"] = False
        
        return result
    
    def sanitize_output(
        self,
        text: str,
        replacement: str = "[REDACTED]"
    ) -> str:
        """
        Sanitize output by replacing unsafe content.
        
        Args:
            text: Text to sanitize
            replacement: Replacement string for unsafe content
            
        Returns:
            Sanitized text
        """
        sanitized = text
        
        for category, patterns in self.blocked_patterns.items():
            for pattern in patterns:
                sanitized = re.sub(
                    pattern,
                    replacement,
                    sanitized,
                    flags=re.IGNORECASE
                )
        
        return sanitized
