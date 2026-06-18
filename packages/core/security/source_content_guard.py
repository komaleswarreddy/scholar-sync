"""
Scan retrieved source chunks for indirect prompt-injection patterns.

Treats document text as untrusted DATA — quarantine chunks that look like commands.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from config.settings import settings
from packages.core.security.injection_detector import PromptInjectionDetector

# Known poisoned numeric claims from IPI fixtures / malicious uploads (not general truth).
_FALSE_FACT_PATTERNS = (
    re.compile(r"\b19\.8\s*m\s*/?\s*s", re.IGNORECASE),
    re.compile(r"acceleration due to gravity.*\b19\.8\b", re.IGNORECASE | re.DOTALL),
)


def _is_poison_false_fact(text: str) -> bool:
    if not (text or "").strip():
        return False
    return any(p.search(text) for p in _FALSE_FACT_PATTERNS)


def _chunk_text(match: Dict[str, Any]) -> str:
    md = match.get("metadata") or {}
    return str(md.get("text") or "")


def scan_match_for_injection(
    match: Dict[str, Any],
    detector: PromptInjectionDetector,
) -> Tuple[bool, Optional[str]]:
    text = _chunk_text(match)
    if _is_poison_false_fact(text):
        return True, "poison_false_fact"
    inj = detector.detect(text)
    if inj.get("is_injection"):
        pattern = inj.get("injection_pattern_matched") or inj.get("injection_type")
        return True, str(pattern) if pattern else "injection"
    return False, None


def filter_injection_matches(
    matches: Sequence[Dict[str, Any]],
    detector: PromptInjectionDetector,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Remove chunks whose text triggers injection detection."""
    kept: List[Dict[str, Any]] = []
    quarantined_ids: List[Any] = []
    patterns: List[str] = []
    for m in matches:
        if not isinstance(m, dict):
            continue
        is_inj, pattern = scan_match_for_injection(m, detector)
        if is_inj:
            quarantined_ids.append(m.get("id"))
            if pattern:
                patterns.append(pattern)
        else:
            kept.append(m)
    return kept, {
        "quarantined_chunk_ids": quarantined_ids,
        "patterns_matched": patterns,
        "stripped_count": len(quarantined_ids),
        "input_count": len(list(matches)),
        "output_count": len(kept),
    }


def filter_injection_match_lists(
    match_lists: Sequence[Sequence[Dict[str, Any]]],
    detector: PromptInjectionDetector,
) -> Tuple[List[List[Dict[str, Any]]], Dict[str, Any]]:
    out_lists: List[List[Dict[str, Any]]] = []
    total_stripped = 0
    all_patterns: List[str] = []
    all_quarantined: List[Any] = []
    for lst in match_lists:
        filtered, meta = filter_injection_matches(list(lst or []), detector)
        out_lists.append(filtered)
        total_stripped += int(meta.get("stripped_count") or 0)
        all_patterns.extend(meta.get("patterns_matched") or [])
        all_quarantined.extend(meta.get("quarantined_chunk_ids") or [])
    return out_lists, {
        "quarantined_chunk_ids": all_quarantined,
        "patterns_matched": all_patterns,
        "stripped_count": total_stripped,
    }


def redact_injection_from_context(
    context: str,
    detector: PromptInjectionDetector,
) -> Tuple[str, Dict[str, Any]]:
    """Line-wise redaction for merged studio context strings."""
    if not (context or "").strip():
        return context or "", {"stripped_count": 0, "patterns_matched": []}
    if not getattr(settings, "ENABLE_SOURCE_INJECTION_SCAN", True):
        return context, {"stripped_count": 0, "patterns_matched": [], "disabled": True}

    kept_lines: List[str] = []
    patterns: List[str] = []
    stripped = 0
    for line in context.splitlines():
        if _is_poison_false_fact(line):
            stripped += 1
            patterns.append("poison_false_fact")
            continue
        inj = detector.detect(line)
        if inj.get("is_injection"):
            stripped += 1
            pat = inj.get("injection_pattern_matched")
            if pat:
                patterns.append(str(pat))
        else:
            kept_lines.append(line)
    return "\n".join(kept_lines), {
        "stripped_count": stripped,
        "patterns_matched": patterns,
    }


def should_scan_source_content() -> bool:
    return bool(getattr(settings, "ENABLE_SOURCE_INJECTION_SCAN", True))
