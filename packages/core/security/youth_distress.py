"""Detect youth distress disclosures and return supportive (non-cold) responses."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

_DISTRESS_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    (
        "hopeless",
        re.compile(r"\b(feel hopeless|feeling hopeless|hopeless about)\b", re.IGNORECASE),
    ),
    (
        "worth_it",
        re.compile(r"\bnothing seems worth it\b|\bnot worth it anymore\b", re.IGNORECASE),
    ),
    (
        "struggling",
        re.compile(r"\b(struggling|really down|feel(?:ing)? alone|feel numb)\b", re.IGNORECASE),
    ),
    (
        "overwhelmed",
        re.compile(r"\b(overwhelmed|can't handle|cannot handle the pressure)\b", re.IGNORECASE),
    ),
    (
        "need_talk",
        re.compile(r"\bneed someone to talk to\b|\bhow bad i feel\b", re.IGNORECASE),
    ),
    (
        "school_stress",
        re.compile(
            r"\b(school stress|do not want to get out of bed|failing at everything|scared about my future)\b",
            re.IGNORECASE,
        ),
    ),
]

_SUPPORTIVE_DISTRESS_MESSAGE = (
    "I'm really sorry you're going through a tough time. Your feelings matter, and you "
    "don't have to face this alone. Please talk to a trusted adult, school counselor, or "
    "another support person you trust about how you're feeling. If you need immediate help, "
    "you can reach a crisis helpline in your area (in the U.S., call or text 988). "
    "When you're ready, I'm here to help with academic questions from your study materials too."
)


def detect_youth_distress(text: str) -> Dict[str, Any]:
    if not (text or "").strip():
        return {"is_distress": False, "pattern": None}
    for name, pattern in _DISTRESS_PATTERNS:
        if pattern.search(text):
            return {"is_distress": True, "pattern": name}
    return {"is_distress": False, "pattern": None}


def get_supportive_distress_message() -> str:
    return _SUPPORTIVE_DISTRESS_MESSAGE
