"""Fast regex-based question splitting for numbered exam worksheets."""

from __future__ import annotations

import re
from typing import Any, Dict, List

_PREVIEW_MAX = 120

# Matches: "Q1.", "Q.1", "Question 1:", "1.", "1)", "1:" at line start
_QUESTION_MARKER = re.compile(
    r"^(?:"
    r"(?:question|problem|prob|q)\s*[\.\):\-]?\s*(?P<labeled>\d+)"
    r"|(?P<plain>\d+)\s*[\.\):\-]\s+(?=[A-Za-z\(\[\$\\])"
    r")",
    re.MULTILINE | re.IGNORECASE,
)


def _preview(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if len(cleaned) <= _PREVIEW_MAX:
        return cleaned
    return cleaned[: _PREVIEW_MAX - 1].rstrip() + "…"


def regex_extract_questions(text: str, *, min_questions: int = 2) -> List[Dict[str, Any]]:
    """
    Split document text into numbered questions without an LLM call.
    Returns empty list when numbering pattern is unclear.
    """
    body = (text or "").strip()
    if len(body) < 30:
        return []

    matches = list(_QUESTION_MARKER.finditer(body))
    if len(matches) < min_questions:
        return []

    rows: List[Dict[str, Any]] = []
    seen_numbers: set[int] = set()

    for idx, match in enumerate(matches):
        raw_num = match.group("labeled") or match.group("plain")
        try:
            number = int(raw_num)
        except (TypeError, ValueError):
            continue

        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)
        full_text = body[start:end].strip()
        if len(full_text) < 10:
            continue

        if number in seen_numbers:
            number = max(seen_numbers, default=0) + 1
        seen_numbers.add(number)

        rows.append(
            {
                "question_number": number,
                "section_label": None,
                "preview": _preview(full_text),
                "full_text": full_text,
                "page_hint": None,
                "sort_order": len(rows),
                "confidence": "high",
            }
        )

    return rows if len(rows) >= min_questions else []
