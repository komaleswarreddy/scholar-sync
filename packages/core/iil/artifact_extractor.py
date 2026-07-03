"""LLM extraction of derived knowledge artifacts from approved candidates."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_EXTRACT_PROMPT = """You are a curriculum knowledge curator. Distill this expert interaction into a structured teaching artifact.

Return JSON only:
{{
  "content": "clear, age-appropriate explanation (200-600 words)",
  "dimension_tags": ["definition"|"intuition"|"misconceptions"|"applications"|"cross_concept"|"mathematical"|"historical"|"exam_traps"|"visual"|"problem_solving"]
}}

Conversation:
{conversation}
"""


async def extract_artifact_from_chain(conversation_text: str) -> Dict[str, Any]:
    """LLM extraction; returns {content, dimension_tags}."""
    from config.settings import settings

    if not settings.OPENAI_API_KEY:
        return {"content": conversation_text[:2000], "dimension_tags": ["definition"]}

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": _EXTRACT_PROMPT.format(conversation=conversation_text[:8000]),
                }
            ],
            max_tokens=1500,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or "{}"
        data = json.loads(raw)
        return {
            "content": data.get("content") or conversation_text[:2000],
            "dimension_tags": data.get("dimension_tags") or ["definition"],
        }
    except Exception as exc:
        logger.warning("Artifact extraction failed: %s", exc)
        return {"content": conversation_text[:2000], "dimension_tags": ["definition"]}
