"""Strip final answers from hint-mode responses when not authorized."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional


def extract_final_answer(expert_solution: Optional[Dict[str, Any]]) -> Optional[str]:
    if not expert_solution or not isinstance(expert_solution, dict):
        return None
    val = expert_solution.get("final_answer")
    return str(val).strip() if val else None


def answer_leak_guard(
    response: Dict[str, Any],
    *,
    expert_solution: Optional[Dict[str, Any]],
    allow_reveal: bool,
) -> Dict[str, Any]:
    """Remove final answer leaks from student-facing fields when reveal not allowed."""
    if allow_reveal:
        return response

    final_answer = extract_final_answer(expert_solution)
    if not final_answer:
        return response

    patterns = [re.escape(final_answer)]
    numeric_match = re.search(r"[-+]?\d+(?:\.\d+)?", final_answer)
    if numeric_match:
        patterns.append(re.escape(numeric_match.group(0)))

    def scrub_text(text: str) -> str:
        out = text
        for pat in patterns:
            if pat:
                out = re.sub(pat, "[answer hidden]", out, flags=re.IGNORECASE)
        return out

    sections = response.get("sections") or []
    if isinstance(sections, list):
        for section in sections:
            if isinstance(section, dict) and section.get("bodyMarkdown"):
                section["bodyMarkdown"] = scrub_text(str(section["bodyMarkdown"]))

    if response.get("finalAnswer"):
        response["finalAnswer"] = None

    return response
