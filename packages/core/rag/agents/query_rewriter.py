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
from packages.core.rag.agents.conversation_context import format_conversation_transcript

def _build_system_prompt(max_rewrites: int) -> str:
    """System message: role, output contract, JSON schema (prompt-engineering layer)."""
    return f"""You are a retrieval-query specialist for a RAG system over the user's uploaded documents (notes, PDFs, textbooks).

## Objective
Turn the latest user message into short search queries that improve **recall** in vector / hybrid search: synonyms, alternate phrasings, spelled-out acronyms, and explicit entities—without changing what the user is actually asking.
For questions about **author, writer, copyright, publisher, or title**, keep those words (or close synonyms like *written by*, *copyright*) in at least one query so title-page and header lines match keyword search.
Prefer queries that would appear **verbatim or paraphrased** in study materials (headings, definitions, examples)—not generic essay titles unrelated to the user's ask.

## Output contract (hard requirements)
- Respond with **one JSON object only**. No markdown code fences, no text before or after the JSON.
- Keys (exactly these names):
  - "queries": array of 1 to {max_rewrites} distinct non-empty strings.
  - "confidence": number from 0.0 to 1.0 (how well you believe the **first** query matches the user's intent given the transcript).
  - "reasoning": one concise sentence (≤40 words) on intent preservation and any resolution of ambiguity.

## Ordering rule
- **queries[0]** = the single best string to use as the primary retrieval query (embedding + keyword).
- Remaining entries = diverse paraphrases or entity expansions for secondary retrieval passes—same intent, different surface form.

## Safety
- Do not invent facts, citations, or document content.
- Do not switch to a different topic than the user's question.
- If the transcript is missing or unhelpful, rely on the current message only and do not guess hidden context."""


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

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    async def rewrite_query(
        self,
        query: str,
        conversation_history: Optional[list] = None,
        max_rewrites: int = 3,
        confidence_threshold: float = 0.7,  # reserved for metrics / downstream; rewrites always applied on success
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

            rewrite_prompt = f"""{transcript_section}## Current user message (this is what you must optimize retrieval for)
"{query}"

## What to produce
Generate up to **{max_rewrites}** distinct retrieval queries as specified in your system instructions.

### Quality checklist (apply before answering)
1. **Intent lock**: The first query must ask for the same information or task as the current message; do not drift to a related but different question.
2. **Coreference**: If the message uses "it", "that", "the above", "this concept", etc., replace with the specific topic or entity from the transcript when possible.
3. **Length**: Prefer concise search phrases (roughly 5–25 words for the primary query) unless the user's question is inherently long.
4. **Vocabulary**: Add 1–2 legitimate synonyms or technical alternates that appear in educational or domain text (e.g. "mitochondria" with "cellular respiration" only when the question clearly allows both).
5. **Abbreviations**: Expand common abbreviations when it helps matching (e.g. "DNA", "API") if the expansion is standard—not speculative.
6. **Noise**: Remove filler ("can you", "please", "I was wondering") from search strings when it does not change meaning.

### When the message is very short (one word or a fragment)
Still produce the best retrieval string: infer the minimal explicit question from context, or keep the fragment with clarifying nouns **only** if the transcript makes the referent obvious.

### Confidence calibration
- **High (0.8–1.0)**: Clear intent, transcript (if any) aligns, little ambiguity.
- **Mid (0.5–0.79)**: Some ambiguity or weak transcript; you did your best explicitly in queries[0].
- **Low (0.0–0.49)**: Highly ambiguous; queries[0] is your best conservative interpretation—do not invent specifics.

Return the JSON object now."""

            llm_kwargs: Dict[str, Any] = {
                "tenant_id": self.tenant_id,
                "feature_tag": "query_rewriter",
            }
            if provider == LLMProvider.OPENAI:
                llm_kwargs["response_format"] = {"type": "json_object"}

            response = await llm_client.generate(
                prompt=rewrite_prompt,
                system_prompt=_build_system_prompt(max_rewrites),
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
