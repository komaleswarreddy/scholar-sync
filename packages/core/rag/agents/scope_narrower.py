"""
Scope Narrowing Agent

Narrows retrieval scope using full user+assistant transcript and structured JSON (OpenAI).
"""

import json
import re
from typing import Any, Dict, List, Optional

from config.settings import settings
from packages.core.llm import get_llm_client, get_model_for_task
from packages.core.llm._base import LLMProvider
from packages.core.prompts import load_prompt
from packages.core.rag.agents.conversation_context import format_conversation_transcript


def _parse_scope_json(content: str) -> Optional[Dict[str, Any]]:
    text = (content or "").strip()
    if not text:
        return None
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and "focused_query" in obj:
            return obj
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        obj = json.loads(m.group())
        if isinstance(obj, dict) and "focused_query" in obj:
            return obj
    except json.JSONDecodeError:
        pass
    return None


class ScopeNarrower:
    """Narrows retrieval scope; conversation-aware."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    async def narrow_scope(
        self,
        query: str,
        available_sources: Optional[List[str]] = None,  # reserved for future source-aware narrowing
        conversation_history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        _ = available_sources
        if not query or not str(query).strip():
            return {
                "focused_query": query or "",
                "key_terms": [],
                "filters": None,
                "max_chunks": 5,
            }

        query = str(query).strip()

        try:
            provider, model = get_model_for_task("scope_narrower")
            llm_client = get_llm_client(provider=provider, model=model, temperature=0.2)

            history_block = format_conversation_transcript(
                conversation_history,
                max_messages=getattr(settings, "AGENT_CONVERSATION_MAX_MESSAGES", 12),
                max_chars_per_message=getattr(settings, "AGENT_CONVERSATION_MAX_CHARS_PER_MESSAGE", 1200),
            )
            ctx = f"\nConversation:\n{history_block}\n" if history_block else ""

            prompt = f"""Analyze this query for information retrieval.{ctx}
Query: {query}

Extract key_terms (3-7), a focused_query string for retrieval (resolve references using conversation),
and max_chunks (3-15) suggested pool size."""

            llm_kwargs: Dict[str, Any] = {
                "tenant_id": self.tenant_id,
                "feature_tag": "scope_narrower",
            }
            if provider == LLMProvider.OPENAI:
                llm_kwargs["response_format"] = {"type": "json_object"}

            response = await llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=400,
                **llm_kwargs,
            )

            parsed = _parse_scope_json(response.content.strip() if response.content else "")
            if not parsed:
                return {
                    "focused_query": query,
                    "key_terms": query.split()[:5],
                    "filters": None,
                    "max_chunks": 5,
                }

            kterms = parsed.get("key_terms") or []
            if isinstance(kterms, str):
                kterms = [kterms]
            kterms = [str(t).strip() for t in kterms if t][:7]

            fq = str(parsed.get("focused_query", query) or query).strip()
            mc = parsed.get("max_chunks", 5)
            try:
                mc = int(mc)
            except (TypeError, ValueError):
                mc = 5
            mc = max(3, min(15, mc))

            return {
                "focused_query": fq or query,
                "key_terms": kterms or query.split()[:5],
                "filters": None,
                "max_chunks": mc,
            }

        except Exception as e:
            print(f"[SCOPE_NARROWER] Error narrowing scope: {e}")
            return {
                "focused_query": query,
                "key_terms": query.split()[:5],
                "filters": None,
                "max_chunks": 5,
            }

    def extract_key_terms(self, query: str) -> List[str]:
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "should",
            "could",
            "may",
            "might",
            "can",
            "what",
            "how",
            "why",
            "when",
            "where",
            "who",
        }

        words = query.lower().split()
        key_terms = [w for w in words if w not in stop_words and len(w) > 2]

        return key_terms[:5]
