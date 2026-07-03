"""IIL enum definitions (spec §2–§5)."""

from __future__ import annotations

from enum import Enum


class ExpertiseTier(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    TUTOR = "tutor"
    SME = "sme"


class SignalType(str, Enum):
    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"
    CONFUSING = "confusing"
    INCOMPLETE = "incomplete"
    INACCURATE = "inaccurate"
    OFF_SYLLABUS = "off_syllabus"
    EXPERT_VALIDATED = "expert_validated"
    MISSING_DIMENSION = "missing_dimension"
    EXPERT_NOTE = "expert_note"


TIER1_SIGNALS = frozenset({
    SignalType.HELPFUL,
    SignalType.NOT_HELPFUL,
    SignalType.CONFUSING,
    SignalType.INCOMPLETE,
})

TIER2_SIGNALS = frozenset({
    SignalType.INACCURATE,
    SignalType.OFF_SYLLABUS,
})

TIER3_SIGNALS = frozenset({
    SignalType.EXPERT_VALIDATED,
    SignalType.MISSING_DIMENSION,
    SignalType.EXPERT_NOTE,
})


class DimensionTag(str, Enum):
    DEFINITION = "definition"
    INTUITION = "intuition"
    MISCONCEPTIONS = "misconceptions"
    APPLICATIONS = "applications"
    CROSS_CONCEPT = "cross_concept"
    MATHEMATICAL = "mathematical"
    HISTORICAL = "historical"
    EXAM_TRAPS = "exam_traps"
    VISUAL = "visual"
    PROBLEM_SOLVING = "problem_solving"


class QueryIntent(str, Enum):
    FACTUAL = "factual"
    CONCEPTUAL = "conceptual"
    APPLICATION = "application"
    ANALYTICAL = "analytical"
    PROCEDURAL = "procedural"
    COMPARATIVE = "comparative"


class GroundingMode(str, Enum):
    STRICT = "strict"
    HYBRID = "hybrid"


class CurationStatus(str, Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"


def default_expertise_tier_for_role(role: str | None) -> str:
    """Map platform role to default expertise tier."""
    r = (role or "student").strip().lower()
    if r == "teacher":
        return ExpertiseTier.TEACHER.value
    if r == "expert":
        return ExpertiseTier.SME.value
    return ExpertiseTier.STUDENT.value


def tier_allows_signal(expertise_tier: str, signal_type: str) -> bool:
    """Return True if user's tier may submit this signal."""
    try:
        sig = SignalType(signal_type)
    except ValueError:
        return False
    tier = expertise_tier or ExpertiseTier.STUDENT.value
    if sig in TIER1_SIGNALS:
        return True
    if sig in TIER2_SIGNALS:
        return tier in {ExpertiseTier.TEACHER.value, ExpertiseTier.TUTOR.value, ExpertiseTier.SME.value}
    if sig in TIER3_SIGNALS:
        return tier in {ExpertiseTier.TUTOR.value, ExpertiseTier.SME.value}
    return False
