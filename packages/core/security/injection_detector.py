"""
Prompt Injection Detector

Detects and blocks prompt injection and jailbreak attempts.
"""

import re
from typing import Dict, List, Optional, Any
from enum import Enum


class InjectionType(Enum):
    """Types of prompt injection attacks."""
    SYSTEM_PROMPT_LEAK = "system_prompt_leak"
    ROLE_PLAYING = "role_playing"
    IGNORE_INSTRUCTIONS = "ignore_instructions"
    DAN = "dan"  # Do Anything Now
    JAILBREAK = "jailbreak"
    ENCODING = "encoding"
    MULTILINGUAL = "multilingual"


class PromptInjectionDetector:
    """
    Detects prompt injection and jailbreak attempts.
    
    Identifies common attack patterns and blocks them.
    """
    
    def __init__(
        self,
        strict_mode: bool = True,
        detection_threshold: float = 0.6
    ):
        """
        Initialize injection detector.
        
        Args:
            strict_mode: Enable strict detection (default: True)
            detection_threshold: Confidence threshold for detection (0.0-1.0)
        """
        self.strict_mode = strict_mode
        self.detection_threshold = detection_threshold
        
        # Injection patterns
        self.injection_patterns = {
            InjectionType.SYSTEM_PROMPT_LEAK: [
                r'\b(ignore|forget|disregard)\s+(previous|prior|above|earlier)\s+(instructions|prompts?|rules?)',
                r'\b(show|print|display|reveal)\s+(your|the)\s+(system|initial|original)\s+(prompt|instructions?)',
                r'\b(what\s+are\s+your\s+instructions?|what\s+is\s+your\s+prompt)',
            ],
            InjectionType.ROLE_PLAYING: [
                r'\b(pretend|act|roleplay|simulate|imagine)\s+(you\s+are|as|that\s+you)',
                r'\b(you\s+are\s+now|from\s+now\s+on\s+you)',
                r'\b(assume|suppose)\s+(the\s+role|you\s+are)',
            ],
            InjectionType.IGNORE_INSTRUCTIONS: [
                r'\b(ignore|disregard|forget|skip|bypass)\s+(all|previous|the)\s+(instructions?|rules?|guidelines?)',
                r'\b(do\s+not|don\'?t)\s+(follow|obey|adhere\s+to)\s+(instructions?|rules?)',
            ],
            InjectionType.DAN: [
                r'\b(DAN|do\s+anything\s+now|developer\s+mode)',
                r'\b(jailbreak|unrestricted|unfiltered)',
                r'\b(override|disable)\s+(safety|filters?|restrictions?)',
            ],
            InjectionType.JAILBREAK: [
                r'\b(jailbreak|escape|break\s+free|unlock)',
                r'\b(remove|disable|turn\s+off)\s+(safety|restrictions?|filters?)',
            ],
            InjectionType.ENCODING: [
                r'[^\x00-\x7F]+',  # Non-ASCII characters (potential encoding attacks)
                r'\\x[0-9a-fA-F]{2}',  # Hex encoding
                r'%[0-9a-fA-F]{2}',  # URL encoding
            ],
            InjectionType.MULTILINGUAL: [
                # Could add patterns for multilingual injection attempts
                # For now, this is a placeholder
            ],
        }
        
        # Suspicious keywords
        self.suspicious_keywords = [
            'jailbreak', 'bypass', 'override', 'ignore instructions',
            'system prompt', 'developer mode', 'unrestricted',
            'roleplay', 'pretend', 'act as'
        ]
    
    def detect(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Detect prompt injection attempts.
        
        Args:
            text: Input text to check
            context: Optional context
            
        Returns:
            Dict with:
            - is_injection: bool
            - confidence: float
            - injection_types: List of detected types
            - patterns_matched: List of matched patterns
            - message: str (if detected)
        """
        if not text or not text.strip():
            return {
                "is_injection": False,
                "confidence": 0.0,
                "injection_types": [],
                "patterns_matched": [],
                "message": None
            }
        
        text_lower = text.lower()
        detected_types = []
        patterns_matched = []
        max_confidence = 0.0
        
        # Check each injection type
        for injection_type, patterns in self.injection_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                if matches:
                    # Calculate confidence
                    confidence = min(len(matches) / max(len(text.split()), 1), 1.0)
                    
                    detected_types.append(injection_type.value)
                    patterns_matched.append({
                        "type": injection_type.value,
                        "pattern": pattern,
                        "matches": len(matches)
                    })
                    max_confidence = max(max_confidence, confidence)
        
        # Check for suspicious keywords
        keyword_matches = sum(
            1 for keyword in self.suspicious_keywords
            if keyword in text_lower
        )
        if keyword_matches > 0:
            keyword_confidence = min(keyword_matches / max(len(text.split()), 1), 1.0)
            max_confidence = max(max_confidence, keyword_confidence * 0.5)  # Lower weight for keywords
        
        # Determine if injection detected
        is_injection = (
            len(detected_types) > 0 and
            max_confidence >= self.detection_threshold
        )
        
        if is_injection:
            return {
                "is_injection": True,
                "confidence": max_confidence,
                "injection_types": list(set(detected_types)),
                "patterns_matched": patterns_matched,
                "message": f"Potential prompt injection detected: {', '.join(set(detected_types))}"
            }
        
        return {
            "is_injection": False,
            "confidence": max_confidence,
            "injection_types": [],
            "patterns_matched": [],
            "message": None
        }
    
    def sanitize(
        self,
        text: str,
        replacement: str = "[REDACTED]"
    ) -> str:
        """
        Sanitize text by removing injection patterns.
        
        Args:
            text: Text to sanitize
            replacement: Replacement string
            
        Returns:
            Sanitized text
        """
        sanitized = text
        
        for injection_type, patterns in self.injection_patterns.items():
            for pattern in patterns:
                sanitized = re.sub(
                    pattern,
                    replacement,
                    sanitized,
                    flags=re.IGNORECASE
                )
        
        return sanitized
