"""
Query Rewriter Agent

Rewrites user queries to improve retrieval recall. Always runs an LLM pass for
non-empty queries (no word-count skips). Uses full user+assistant transcript
context and structured JSON output on OpenAI.
"""

import json
import re
from typing import Any, Dict, List, Optional

from config.settings import settings
from packages.core.llm import get_llm_client, get_model_for_task
from packages.core.llm._base import LLMProvider
from packages.core.prompts import load_prompt
from packages.core.rag.agents.conversation_context import (
    format_conversation_transcript,
    format_routing_hints_section,
)


def _parse_rewrite_json(content: str) -> Optional[Dict[str, Any]]:
    text = (content or "").strip()
    if not text:
        return None
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and "queries" in obj:
            return obj
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        obj = json.loads(match.group())
        if isinstance(obj, dict) and "queries" in obj:
            return obj
    except json.JSONDecodeError:
        pass
    return None


class QueryRewriter:
    """
    Rewrites queries for hybrid / vector retrieval with conversation-aware context.
    """

    def __init__(self, tenant_id: str, user_id: Optional[str] = None):
        self.tenant_id = tenant_id
        self.user_id = user_id

    async def rewrite_query(
        self,
        query: str,
        conversation_history: Optional[list] = None,
        max_rewrites: int = 3,
        confidence_threshold: float = 0.7,  # reserved for metrics / downstream; rewrites always applied on success
        feature_tag: str = "query_rewriter",
        scope: Optional[str] = None,
        requires_retrieval: Optional[bool] = None,
        requires_attachment: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Rewrite query to improve retrieval recall while preserving semantic intent.

        Returns:
            - queries: best retrieval string first, then alternate phrasings
            - confidence: model self-reported confidence
            - used_rewrites: True when LLM returned usable variants (always on success)
        """
        if not query or not query.strip():
            return {
                "queries": [query or ""],
                "confidence": 1.0,
                "used_rewrites": False,
                "reasoning": "empty query",
            }

        query = query.strip()

        try:
            provider, model = get_model_for_task("query_rewriter")
            llm_client = get_llm_client(provider=provider, model=model, temperature=0.25)

            history_block = format_conversation_transcript(
                conversation_history,
                max_messages=getattr(settings, "AGENT_CONVERSATION_MAX_MESSAGES", 12),
                max_chars_per_message=getattr(settings, "AGENT_CONVERSATION_MAX_CHARS_PER_MESSAGE", 1200),
            )
            transcript_section = ""
            if history_block:
                transcript_section = (
                    "## Prior conversation (oldest → newest; use to resolve pronouns and implicit references)\n"
                    f"{history_block}\n\n"
                )
            else:
                transcript_section = "## Prior conversation\nNone provided—treat the current message as standalone.\n\n"

            system_prompt = load_prompt(
                "agents/query_rewriter_system.j2",
                max_rewrites=max_rewrites,
            )
            rewrite_prompt = load_prompt(
                "agents/query_rewriter_user.j2",
                transcript_section=transcript_section,
                routing_hints_section=format_routing_hints_section(
                    scope=scope,
                    requires_retrieval=requires_retrieval,
                    requires_attachment=requires_attachment,
                ),
                query=query,
                max_rewrites=max_rewrites,
            )

            llm_kwargs: Dict[str, Any] = {
                "tenant_id": self.tenant_id,
                "feature_tag": feature_tag,
            }
            if self.user_id:
                llm_kwargs["user_id"] = self.user_id
            if provider == LLMProvider.OPENAI:
                llm_kwargs["response_format"] = {"type": "json_object"}

            response = await llm_client.generate(
                prompt=rewrite_prompt,
                system_prompt=system_prompt,
                temperature=0.25,
                max_tokens=650,
                **llm_kwargs,
            )

            parsed = _parse_rewrite_json(response.content.strip() if response.content else "")
            if not parsed:
                return {
                    "queries": [query],
                    "confidence": 0.0,
                    "used_rewrites": False,
                    "reasoning": "Failed to parse rewrite response",
                }

            raw_list = parsed.get("queries") or []
            rewritten_queries = [
                str(q).strip()
                for q in raw_list[: max_rewrites + 2]
                if q and str(q).strip()
            ]
            confidence = float(parsed.get("confidence", 0.75))

            if not rewritten_queries:
                rewritten_queries = [query]
            elif query not in rewritten_queries:
                # Keep model order (best first); ensure focused query is included for merge/fallback
                rewritten_queries.append(query)

            # Successful LLM parse: always treat as rewrite applied (no complexity-based skip)
            used_rewrites = True

            return {
                "queries": rewritten_queries[: max_rewrites + 1],
                "confidence": confidence,
                "used_rewrites": used_rewrites,
                "reasoning": str(parsed.get("reasoning", "") or ""),
            }

        except Exception as e:
            print(f"[QUERY_REWRITER] Error rewriting query: {e}")
            return {
                "queries": [query],
                "confidence": 0.0,
                "used_rewrites": False,
                "reasoning": f"Error: {str(e)}",
            }
