"""
Intent Classifier

Classifies user intent for downstream routing (RAG depth, whole-document map-reduce,
retrieval breadth, etc.). Uses a single LLM pass with strict JSON output; optional
conversation context is included when provided.

Observability: feature_usage records llm_ok | llm_parse_fail | llm_error.
"""

from enum import Enum
import json
import re
import time
from typing import Any, Dict, List, Optional

from config.settings import settings
from packages.core.llm import get_llm_client, get_model_for_task
from packages.core.llm._base import LLMProvider
from packages.core.monitoring.metrics import get_metrics_collector
from packages.core.prompts import load_prompt
from packages.core.rag.agents.conversation_context import format_conversation_transcript

# LLM-only: slightly higher token budget for calibrated confidence + short rationale.
_INTENT_MAX_TOKENS = 320


class UserIntent(str, Enum):
    """User intent types."""

    CONVERSATIONAL = "conversational"
    QUESTION = "question"
    EXPLANATION = "explanation"
    SUMMARY = "summary"
    WHOLE_DOCUMENT_SUMMARY = "whole_document_summary"
    COMPARISON = "comparison"
    DEFINITION = "definition"
    HOW_TO = "how_to"
    ANALYSIS = "analysis"
    CREATION = "creation"
    GENERAL = "general"


_INTENT_MAP = {
    "conversational": UserIntent.CONVERSATIONAL,
    "chat_only": UserIntent.CONVERSATIONAL,
    "question": UserIntent.QUESTION,
    "explanation": UserIntent.EXPLANATION,
    "summary": UserIntent.SUMMARY,
    "whole_document_summary": UserIntent.WHOLE_DOCUMENT_SUMMARY,
    "comparison": UserIntent.COMPARISON,
    "definition": UserIntent.DEFINITION,
    "how_to": UserIntent.HOW_TO,
    "analysis": UserIntent.ANALYSIS,
    "creation": UserIntent.CREATION,
    "general": UserIntent.GENERAL,
}


def _parse_intent_json(content: str) -> Optional[Dict[str, Any]]:
    """Parse model output into a dict; try strict JSON first, then brace extraction."""
    text = (content or "").strip()
    if not text:
        return None
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and "intent" in obj:
            return obj
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
    if not match:
        match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        obj = json.loads(match.group())
        if isinstance(obj, dict) and "intent" in obj:
            return obj
    except json.JSONDecodeError:
        pass
    return None


def _llm_failure_return(reason: str) -> Dict[str, Any]:
    """Safe default when LLM fails or output is unparseable (still structured for downstream)."""
    return {
        "intent": UserIntent.GENERAL,
        "confidence": 0.35,
        "reasoning": reason,
    }


def _record_intent_path(
    tenant_id: str,
    endpoint: str,
    extra_ms: Optional[float] = None,
) -> None:
    """Lightweight feature_usage row for intent_classifier observability."""
    try:
        mc = get_metrics_collector()
        parts = [endpoint]
        if extra_ms is not None:
            parts.append(f"ms={extra_ms:.1f}")
        mc.record_feature_usage(
            tenant_id=tenant_id,
            feature="intent_classifier",
            endpoint="|".join(parts),
        )
    except Exception:
        pass


class IntentClassifier:
    """
    LLM-only intent router for the RAG / chat pipeline.

    Every non-empty query runs one classification call (structured JSON). Empty query
    returns general without calling the model.
    """

    def __init__(self, tenant_id: str, user_id: Optional[str] = None):
        self.tenant_id = tenant_id
        self.user_id = user_id

    async def classify_intent(
        self,
        query: str,
        conversation_history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Classify user intent via the routing LLM.

        Returns:
            Dict with keys: intent (UserIntent), confidence (float), reasoning (str).
        """
        if not query:
            return {
                "intent": UserIntent.GENERAL,
                "confidence": 0.5,
                "reasoning": "Empty query",
            }

        t0 = time.perf_counter()
        provider, model = get_model_for_task("intent_classifier")
        llm_client = get_llm_client(provider=provider, model=model, temperature=0.1)

        history_context = ""
        if conversation_history:
            history_context = format_conversation_transcript(
                conversation_history,
                max_messages=getattr(settings, "AGENT_CONVERSATION_MAX_MESSAGES", 12),
                max_chars_per_message=getattr(settings, "AGENT_CONVERSATION_MAX_CHARS_PER_MESSAGE", 1200),
            )

        context_block = ""
        if history_context:
            context_block = f"## Conversation context (oldest → newest)\n{history_context}\n\n"

        prompt = load_prompt(
            "agents/intent_classifier_user.j2",
            query=query.strip(),
            context_block=context_block,
        )
        system_prompt = load_prompt("agents/intent_classifier_system.j2")

        llm_kwargs: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "feature_tag": "intent_classifier",
        }
        if self.user_id:
            llm_kwargs["user_id"] = self.user_id
        if provider == LLMProvider.OPENAI:
            llm_kwargs["response_format"] = {"type": "json_object"}

        try:
            response = await llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.1,
                max_tokens=_INTENT_MAX_TOKENS,
                **llm_kwargs,
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            print(f"[INTENT_CLASSIFIER] Error classifying intent: {e}")
            _record_intent_path(self.tenant_id, "llm_error", extra_ms=elapsed_ms)
            return _llm_failure_return(f"LLM classification failed: {type(e).__name__}")

        elapsed_ms = (time.perf_counter() - t0) * 1000
        parsed = _parse_intent_json(response.content.strip() if response.content else "")

        if not parsed:
            _record_intent_path(self.tenant_id, "llm_parse_fail", extra_ms=elapsed_ms)
            return _llm_failure_return("Model returned invalid or non-JSON intent payload")

        intent_str = str(parsed.get("intent", "general")).lower().strip()
        intent = _INTENT_MAP.get(intent_str, UserIntent.GENERAL)

        try:
            conf = float(parsed.get("confidence", 0.7))
            conf = max(0.0, min(1.0, conf))
        except (TypeError, ValueError):
            conf = 0.6

        _record_intent_path(self.tenant_id, "llm_ok", extra_ms=elapsed_ms)

        return {
            "intent": intent,
            "confidence": conf,
            "reasoning": str(parsed.get("reasoning", "") or "").strip(),
        }
