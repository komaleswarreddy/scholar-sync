"""Two-stage answering: try mini context first, expand on heuristic failure."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


_NOT_FOUND_PATTERNS = (
    r"not found",
    r"cannot find",
    r"no information",
    r"insufficient",
    r"don't have enough",
    r"do not have enough",
    r"not mentioned",
    r"not available in",
    r"unable to answer",
)


def should_use_mini_context(
    *,
    intent: Optional[str],
    query: str,
    match_count: int,
    whole_file_summary: bool = False,
    map_reduce_ok: bool = False,
) -> bool:
    if whole_file_summary or map_reduce_ok:
        return False
    if match_count < 2:
        return False
    intent_l = (intent or "").lower()
    if intent_l in ("summary", "whole_document_summary", "analysis", "comparison"):
        return False
    words = len((query or "").split())
    return words < 15


def build_mini_context(
    matches: List[Dict[str, Any]],
    *,
    n: int = 2,
) -> Tuple[str, List[Dict[str, Any]]]:
    from packages.core.rag.context_packer import pack_context_by_source

    selected = list(matches[: max(1, n)])
    context, citations = pack_context_by_source(selected)
    return context, citations


def should_expand(
    answer: str,
    *,
    context_grounding_blocked: bool = False,
    context_required: bool = True,
    citations: Optional[List[Dict[str, Any]]] = None,
) -> bool:
    if context_grounding_blocked:
        return True
    text = (answer or "").strip().lower()
    if not text:
        return True
    if context_required and not (citations or []):
        return True
    for pat in _NOT_FOUND_PATTERNS:
        if re.search(pat, text):
            return True
    return False
