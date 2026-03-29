"""
Helpers for document metadata / attribution questions (author, publisher, etc.).

These queries often need title-page, copyright, or header chunks; pure semantic
search on the conversational question alone can miss them.
"""

from __future__ import annotations

import re
from typing import List

_METADATA_RE = re.compile(
    r"\b(author|authors|authored|who wrote|written by|copyright|publisher|"
    r"publishing|byline|title page|isbn|edition|citation information)\b",
    re.IGNORECASE,
)

# Direct factual / history questions whose wording may not align with chunk phrasing
_FACTUAL_RECALL_RE = re.compile(
    r"\b(who|whom|when|what year|which year|first|earliest|originally|"
    r"transplant|transplantation|discovered|invented|founded|performed by|done by)\b",
    re.IGNORECASE,
)


def is_metadata_attribution_query(text: str) -> bool:
    if not text or not text.strip():
        return False
    return bool(_METADATA_RE.search(text))


def extra_retrieval_variants(focused_query: str) -> List[str]:
    """Short paraphrases that improve recall for bibliographic fields."""
    q = (focused_query or "").strip()
    if not q:
        return []
    return [
        f"{q} author title copyright",
        "book author publisher title page",
    ]


def is_factual_recall_query(text: str) -> bool:
    """True for who/when/first/... style questions that need keyword + semantic recall."""
    if not text or not text.strip():
        return False
    return bool(_FACTUAL_RECALL_RE.search(text))


def extra_factual_retrieval_variants(focused_query: str) -> List[str]:
    """Extra search strings to surface rare entities and timeline facts in long PDFs."""
    q = (focused_query or "").strip()
    if not q:
        return []
    words = [w for w in re.split(r"\W+", q.lower()) if len(w) > 2]
    key_terms = " ".join(words[:14])
    return [
        f"{key_terms} history details facts",
        f"{key_terms} background timeline",
        f"{key_terms} key people dates",
    ]

