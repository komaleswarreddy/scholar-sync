"""
Utilities for the \"Summarize chat so far\" button.

We keep this logic separate so the API route can be thin and unit-testable.
"""

from __future__ import annotations

from typing import Iterable, List, Tuple


CHAT_SUMMARY_PREFIX = "Summary of this chat so far:"


def filter_out_prior_summaries(messages: Iterable[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """
    Drop previously-generated in-thread summaries to avoid recursive summarization.

    Args:
        messages: iterable of (role, content)
    """
    out: List[Tuple[str, str]] = []
    for role, content in messages:
        c = (content or "").strip()
        if c.startswith(CHAT_SUMMARY_PREFIX):
            continue
        out.append((role, content))
    return out


def format_conversation_lines(messages: Iterable[Tuple[str, str]]) -> str:
    """
    Convert (role, content) pairs into a plain transcript for LLM summarization.
    """
    lines: List[str] = []
    for role, content in messages:
        r = (role or "user").strip().lower()
        label = "User" if r == "user" else "Assistant"
        c = (content or "").strip()
        if not c:
            continue
        lines.append(f"{label}: {c}")
    return "\n".join(lines)

