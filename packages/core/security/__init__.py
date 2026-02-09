"""
Security Package

Phase 5: Security & Student Guardrails
- Input/output moderation
- Safe refusal templates
- Prompt injection detection
- Syllabus-locked RAG
- Academic-only intent enforcement
- PII detection and redaction
"""

from packages.core.security.safety_filter import SafetyFilter, SafetyCategory
from packages.core.security.refusal_templates import RefusalTemplates, RefusalReason
from packages.core.security.injection_detector import PromptInjectionDetector, InjectionType
from packages.core.security.restricted_retriever import RestrictedRetriever
from packages.core.security.intent_gate import IntentGate, IntentCategory
from packages.core.security.pii_detector import PIIDetector, PIIType

__all__ = [
    "SafetyFilter",
    "SafetyCategory",
    "RefusalTemplates",
    "RefusalReason",
    "PromptInjectionDetector",
    "InjectionType",
    "RestrictedRetriever",
    "IntentGate",
    "IntentCategory",
    "PIIDetector",
    "PIIType",
]
