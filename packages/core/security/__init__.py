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
from packages.core.security.academic_integrity import detect_cheating_request
from packages.core.security.openai_moderation import (
    check_moderation,
    moderation_indicates_block,
    moderation_indicates_block_output,
    is_openai_moderation_configured,
)

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
    "detect_cheating_request",
    "check_moderation",
    "moderation_indicates_block",
    "moderation_indicates_block_output",
    "is_openai_moderation_configured",
]
