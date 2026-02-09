"""
PII Detector

Detects and redacts personally identifiable information.
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum


class PIIType(Enum):
    """Types of PII."""
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    NAME = "name"
    ADDRESS = "address"
    DATE_OF_BIRTH = "date_of_birth"
    IP_ADDRESS = "ip_address"


class PIIDetector:
    """
    Detects and redacts personally identifiable information.
    
    Identifies PII patterns and masks them.
    """
    
    def __init__(
        self,
        redact_mode: bool = True,
        mask_char: str = "*"
    ):
        """
        Initialize PII detector.
        
        Args:
            redact_mode: Enable redaction (default: True)
            mask_char: Character to use for masking
        """
        self.redact_mode = redact_mode
        self.mask_char = mask_char
        
        # PII patterns
        self.pii_patterns = {
            PIIType.EMAIL: [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            ],
            PIIType.PHONE: [
                r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # US phone
                r'\b\(\d{3}\)\s?\d{3}[-.]?\d{4}\b',  # (123) 456-7890
                r'\b\+1[-.]?\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # +1-123-456-7890
            ],
            PIIType.SSN: [
                r'\b\d{3}-\d{2}-\d{4}\b',  # 123-45-6789
                r'\b\d{9}\b',  # 123456789 (if in SSN context)
            ],
            PIIType.CREDIT_CARD: [
                r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',  # 1234-5678-9012-3456
                r'\b\d{13,19}\b',  # Generic card number
            ],
            PIIType.IP_ADDRESS: [
                r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',  # IPv4
            ],
            PIIType.DATE_OF_BIRTH: [
                r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # MM/DD/YYYY
            ],
        }
        
        # Common name patterns (less reliable, but can detect)
        self.name_patterns = [
            r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b',  # First Last
            r'\b(Mr\.|Mrs\.|Ms\.|Dr\.)\s+[A-Z][a-z]+\b',  # Title Name
        ]
    
    def detect(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Detect PII in text.
        
        Args:
            text: Text to check
            context: Optional context
            
        Returns:
            Dict with:
            - has_pii: bool
            - pii_types: List of detected types
            - matches: List of matched PII
            - count: int
        """
        if not text or not text.strip():
            return {
                "has_pii": False,
                "pii_types": [],
                "matches": [],
                "count": 0
            }
        
        detected_types = []
        all_matches = []
        
        # Check each PII type
        for pii_type, patterns in self.pii_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    detected_types.append(pii_type.value)
                    all_matches.append({
                        "type": pii_type.value,
                        "value": match.group(),
                        "start": match.start(),
                        "end": match.end()
                    })
        
        # Check for names (less reliable)
        for pattern in self.name_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                # Additional validation: check if it's a common name pattern
                # (This is a simple heuristic - could be improved)
                detected_types.append(PIIType.NAME.value)
                all_matches.append({
                    "type": PIIType.NAME.value,
                    "value": match.group(),
                    "start": match.start(),
                    "end": match.end()
                })
        
        return {
            "has_pii": len(all_matches) > 0,
            "pii_types": list(set(detected_types)),
            "matches": all_matches,
            "count": len(all_matches)
        }
    
    def redact(
        self,
        text: str,
        pii_types: Optional[List[PIIType]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Redact PII from text.
        
        Args:
            text: Text to redact
            pii_types: Optional list of PII types to redact (None = all)
            
        Returns:
            Tuple of (redacted_text, detection_info)
        """
        detection = self.detect(text)
        
        if not detection["has_pii"]:
            return text, detection
        
        redacted = text
        redacted_count = 0
        
        # Redact each match
        for match in reversed(detection["matches"]):  # Reverse to preserve indices
            pii_type = PIIType(match["type"])
            
            # Check if should redact this type
            if pii_types and pii_type not in pii_types:
                continue
            
            # Create mask
            original_value = match["value"]
            if pii_type == PIIType.EMAIL:
                # Mask email: keep first char and domain
                parts = original_value.split("@")
                if len(parts) == 2:
                    masked = f"{parts[0][0]}{self.mask_char * (len(parts[0]) - 1)}@{parts[1]}"
                else:
                    masked = self.mask_char * len(original_value)
            elif pii_type == PIIType.PHONE:
                # Mask phone: keep last 4 digits
                digits = re.sub(r'\D', '', original_value)
                if len(digits) >= 4:
                    masked = f"{self.mask_char * (len(digits) - 4)}{digits[-4:]}"
                else:
                    masked = self.mask_char * len(original_value)
            elif pii_type == PIIType.SSN:
                # Mask SSN: show only last 4
                digits = re.sub(r'\D', '', original_value)
                if len(digits) == 9:
                    masked = f"XXX-XX-{digits[-4:]}"
                else:
                    masked = self.mask_char * len(original_value)
            else:
                # Generic masking: keep first and last char if possible
                if len(original_value) > 2:
                    masked = f"{original_value[0]}{self.mask_char * (len(original_value) - 2)}{original_value[-1]}"
                else:
                    masked = self.mask_char * len(original_value)
            
            # Replace in text
            redacted = (
                redacted[:match["start"]] +
                masked +
                redacted[match["end"]:]
            )
            redacted_count += 1
        
        detection["redacted_count"] = redacted_count
        
        return redacted, detection
    
    def mask_all(
        self,
        text: str
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Mask all detected PII.
        
        Args:
            text: Text to mask
            
        Returns:
            Tuple of (masked_text, detection_info)
        """
        return self.redact(text, pii_types=None)
