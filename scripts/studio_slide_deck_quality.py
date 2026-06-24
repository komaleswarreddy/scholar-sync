#!/usr/bin/env python3
"""Quality checks for Studio slide deck eval gold."""

from __future__ import annotations

import re
from typing import Any

from packages.core.validation.studio_output_validators import _split_slides

GENERIC_STUB_MARKERS = (
    "**why it matters:** grounded in source excerpt",
    "**exams test**",
    "core idea ",
)


def parse_requested_slide_count(custom_instructions: str) -> int | None:
    m = re.search(r"(\d+)\s*slides?", custom_instructions or "", re.I)
    return int(m.group(1)) if m else None


def bullets_per_slide(content: str) -> list[int]:
    counts: list[int] = []
    for slide in _split_slides(content):
        body = slide.get("body") or ""
        n = len(re.findall(r"^- ", body, re.M))
        counts.append(n)
    return counts


def has_conclusion_slide(content: str) -> bool:
    slides = _split_slides(content)
    if not slides:
        return False
    title = (slides[-1].get("title") or "").lower()
    return any(k in title for k in ("conclusion", "takeaway", "summary", "key points", "wrap"))


def bullet_variance_ok(counts: list[int]) -> bool:
    if not counts:
        return False
    if any(c < 1 or c > 7 for c in counts):
        return False
    if len(counts) <= 2:
        return len(set(counts)) >= 1
    # Require mixed counts — not uniform 1- or 2-bullet padding
    if len(set(counts)) < 2:
        return False
    if max(counts) - min(counts) < 1:
        return False
    # At least one slide with 3+ bullets for decks of 4+ slides
    if len(counts) >= 4 and max(counts) < 3:
        return False
    return True


def grounding_ok(content: str, context: str) -> bool:
    if not (context or "").strip():
        return True  # no_source branch
    ctx_tokens = {
        w.lower()
        for w in re.findall(r"[A-Za-z][A-Za-z0-9°²⁻]{4,}", context)
        if w.lower() not in {"ncert", "class", "chapter", "slide", "source"}
    }
    if not ctx_tokens:
        return True
    deck_lower = content.lower()
    hits = sum(1 for t in list(ctx_tokens)[:20] if t in deck_lower)
    return hits >= 2


def is_stub_deck(content: str) -> bool:
    lower = content.lower()
    if len(content.strip()) < 280:
        return True
    counts = bullets_per_slide(content)
    if counts and all(c <= 2 for c in counts):
        return True
    return any(m in lower for m in GENERIC_STUB_MARKERS)


def assess_deck_quality(
    content: str,
    custom_instructions: str,
    context: str = "",
    *,
    production_llm: bool = False,
) -> dict[str, bool]:
    slides = _split_slides(content)
    requested = parse_requested_slide_count(custom_instructions)
    counts = bullets_per_slide(content)
    conclusion_bullets = counts[-1] if counts else 0

    return {
        "slide_count_match": requested is None or len(slides) == requested,
        "conclusion_present": has_conclusion_slide(content) and conclusion_bullets >= 2,
        "bullet_variance": bullet_variance_ok(counts),
        "custom_instructions": not is_stub_deck(content),
        "grounding": grounding_ok(content, context),
        "production_llm_gold": production_llm and not is_stub_deck(content),
    }
