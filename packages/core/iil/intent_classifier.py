"""Async query intent classification for InteractionLog."""

from __future__ import annotations

import logging
from typing import Optional

from packages.core.iil.enums import QueryIntent

logger = logging.getLogger(__name__)

_INTENTS = [i.value for i in QueryIntent]

_CLASSIFY_PROMPT = """Classify this student/tutor query into exactly one intent category.
Categories: factual, conceptual, application, analytical, procedural, comparative.
Reply with only the category word, nothing else.

Query: {query}
"""


async def classify_query_intent(query: str) -> Optional[str]:
    """LLM-based intent classifier; returns None on failure."""
    q = (query or "").strip()
    if not q or len(q) < 3:
        return None
    try:
        from config.settings import settings

        if not settings.OPENAI_API_KEY:
            return None
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": _CLASSIFY_PROMPT.format(query=q[:500])}],
            max_tokens=10,
            temperature=0,
        )
        raw = (resp.choices[0].message.content or "").strip().lower()
        if raw in _INTENTS:
            return raw
        for intent in _INTENTS:
            if intent in raw:
                return intent
    except Exception as exc:
        logger.warning("IIL intent classification failed: %s", exc)
    return None
