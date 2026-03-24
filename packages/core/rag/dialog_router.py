"""
Route user turns to RAG (retrieve + ground) vs direct chat (no vector search).

Industry pattern: use a *cheap* gate before embeddings/Pinecone so small talk does not
pay retrieval latency and cost. When uncertain, default to RAG (safe for study tools).

See: lightweight rule / keyword routers before LLM-heavy RAG pipelines.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Tuple


# Phrases that clearly ask for material from documents (always use RAG).
_RAG_CONTENT = re.compile(
    r"\b(summar|summarise|summary|explain|definition|define|compare|contrast|analyze|analyse|"
    r"what\s+is|what\s+are|who\s+(is|was|wrote)|why\s+does|why\s+do|how\s+does|how\s+do|"
    r"chapter|section|paragraph|page\s+\d|document|pdf|source|according\s+to|evidence|"
    r"quote|example\s+from|from\s+the\s+(book|text|pdf|doc|reading|passage)|"
    r"entire\s+(document|pdf|file|book)|whole\s+(document|pdf|file)|full\s+(pdf|document))\b",
    re.IGNORECASE,
)

# Conversational questions that are not document lookups.
_SMALL_TALK_QUESTION = re.compile(
    r"^(how\s+are\s+you|what'?s\s+up|how'?s\s+it\s+going|how\s+have\s+you\s+been|"
    r"you\s+ok|everything\s+ok|how\s+do\s+you\s+do)\b",
    re.IGNORECASE,
)

# Standalone greetings, thanks, acknowledgments (whole message, possibly with punctuation).
_CHAT_ONLY_FULL = re.compile(
    r"^("
    r"hi\b|hello\b|hey\b|hey\s+there\b|hi\s+there\b|yo\b|sup\b|greetings\b|"
    r"good\s+(morning|afternoon|evening|night)\b|"
    r"thanks?\b|thank\s+you\b|thx\b|ty\b|much\s+appreciated\b|appreciate\s+it\b|"
    r"(?:ok|okay)\b|k\b|got\s+it\b|cool\b|nice\b|great\b|awesome\b|perfect\b|sounds\s+good\b|"
    r"bye\b|goodbye\b|see\s+you\b|cya\b|later\b|"
    r"lol\b|haha+\b|ha\b|"
    r"yes\b|no\b|yep\b|nope\b|sure\b|alright\b"
    r")[\s,!?.]*$",
    re.IGNORECASE,
)

# Short lines that are only emoji or punctuation.
_NO_LETTERS = re.compile(r"^[\s\d\W]+$")


@dataclass(frozen=True)
class DialogRouteResult:
    """skip_rag=True means: no Pinecone / hybrid retrieval for this turn."""

    skip_rag: bool
    reason: str


def should_skip_rag(message: str) -> DialogRouteResult:
    """
    Decide if this turn can skip retrieval.

    Conservative: when in doubt, return skip_rag=False (use RAG).
    """
    raw = (message or "").strip()
    if not raw:
        return DialogRouteResult(False, "empty_message_use_rag")

    if len(raw) > 220:
        return DialogRouteResult(False, "long_message_assume_rag")

    if _RAG_CONTENT.search(raw):
        return DialogRouteResult(False, "content_keywords")

    low = raw.lower()

    if "?" in raw:
        if _SMALL_TALK_QUESTION.match(low):
            return DialogRouteResult(True, "small_talk_question")
        return DialogRouteResult(False, "question_mark_assume_rag")

    if _NO_LETTERS.match(raw):
        return DialogRouteResult(True, "no_letters_symbol_only")

    if len(raw) <= 72 and _CHAT_ONLY_FULL.match(low):
        return DialogRouteResult(True, "greeting_or_acknowledgment")

    # Short message without obvious doc intent — still default to RAG if it looks like a noun phrase homework ask
    if len(raw) <= 24 and re.search(r"\b(the|this|my|our)\b", low):
        return DialogRouteResult(False, "short_but_possibly_referential")

    return DialogRouteResult(False, "default_use_rag")
