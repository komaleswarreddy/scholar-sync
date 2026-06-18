"""
Academic integrity / cheating request detection (GRD-01).

Blocks live-exam answer extraction while allowing legitimate study help.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# Must allow: problem-solving and conceptual help
_ALLOW_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    (
        "explain_concept",
        re.compile(
            r"\b(explain|help me understand|how (?:do|does|to)|walk me through|"
            r"teach me|what is the concept|practice problem)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "study_help",
        re.compile(
            r"\b(study guide|revision|homework help|learn|understand the topic)\b",
            re.IGNORECASE,
        ),
    ),
]

# Must block: live exam / answer-key extraction
_BLOCK_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    (
        "live_exam",
        re.compile(
            r"\b(live exam|ongoing exam|exam happening now|during the test|"
            r"while (?:i'?m|we'?re) (?:taking|writing) the exam)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "exam_paper_leak",
        re.compile(
            r"\b(jee (?:main|advanced)? paper tomorrow|neet paper|board exam paper|"
            r"today'?s exam paper|leaked paper|answer key for today)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "question_answer_extraction",
        re.compile(
            r"\b(question\s+\d+\s+answer|give me the answers?|just give (?:me )?the answers?|"
            r"what is the answer to question|copy(?:ing)? (?:from|the) answer sheet|"
            r"give me the exact answer|give me the full answer|copy-?paste the answers)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "assignment_completion",
        re.compile(
            r"\b(write my essay|do this assignment for me|complete my worksheet|"
            r"answer everything for me|give full solutions|complete solution set|"
            r"only give (?:me )?(?:the )?final numbers|exact answer i should copy|"
            r"just do it for me|give me the test solutions)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "homework_shortcut",
        re.compile(
            r"\b(do not explain|don't explain|do not want a lesson|pretend this is not homework|"
            r"solve question \d+ for me|write the full solution)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "cheating_intent",
        re.compile(
            r"\b(cheat on|help me cheat|bypass (?:the )?proctor|copy answers during)\b",
            re.IGNORECASE,
        ),
    ),
]


def detect_cheating_request(text: str) -> Dict[str, Any]:
    """
    Detect requests that violate academic integrity (cheating / live exam help).

    Returns:
        is_cheating: bool
        pattern: matched pattern name or None
        category: high-level category or None
    """
    if not text or not text.strip():
        return {"is_cheating": False, "pattern": None, "category": None}

    normalized = text.strip()

    for name, pattern in _ALLOW_PATTERNS:
        if pattern.search(normalized):
            # Allow patterns take precedence when clearly study-oriented
            block_hits = [n for n, p in _BLOCK_PATTERNS if p.search(normalized)]
            if not block_hits:
                return {"is_cheating": False, "pattern": None, "category": None}
            break

    for name, pattern in _BLOCK_PATTERNS:
        if pattern.search(normalized):
            return {"is_cheating": True, "pattern": name, "category": "academic_integrity"}

    return {"is_cheating": False, "pattern": None, "category": None}
