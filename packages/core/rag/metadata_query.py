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

