"""
Intent Classifier

Classifies user intent to enable correct routing of tasks.
Determines what type of query the user is asking.

Hybrid flow: quick rules first (no LLM when confidence is high); otherwise LLM with
structured JSON (OpenAI JSON mode when available) plus metrics on path and parse outcome.
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
from packages.core.rag.agents.conversation_context import format_conversation_transcript


# Skip LLM when quick heuristics are this confident or higher (matches cost/latency tradeoff).
QUICK_CONFIDENCE_THRESHOLD = 0.8

_INTENT_SYSTEM_PROMPT = """You are a strict JSON classifier. Reply with a single JSON object only.
Keys: "intent" (string), "confidence" (number 0-1), "reasoning" (string).
Allowed intent values: question, explanation, summary, whole_document_summary, comparison, definition, how_to, analysis, creation, general.
No markdown, no prose outside JSON."""


class UserIntent(str, Enum):
    """User intent types."""
    QUESTION = "question"  # Asking a question
    EXPLANATION = "explanation"  # Requesting explanation
    SUMMARY = "summary"  # Requesting summary
    WHOLE_DOCUMENT_SUMMARY = "whole_document_summary"  # Summarize entire selected file(s) via map-reduce
    COMPARISON = "comparison"  # Comparing concepts
    DEFINITION = "definition"  # Asking for definition
    HOW_TO = "how_to"  # Asking how to do something
    ANALYSIS = "analysis"  # Requesting analysis
    CREATION = "creation"  # Creating content (quiz, flashcards, etc.)
    GENERAL = "general"  # General conversation


_INTENT_MAP = {
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


def _record_intent_path(
    tenant_id: str,
    endpoint: str,
    extra_ms: Optional[float] = None,
    quick_confidence: Optional[float] = None,
) -> None:
    """Lightweight feature_usage row for intent_classifier:rule|llm_ok|llm_fallback."""
    try:
        mc = get_metrics_collector()
        parts = [endpoint]
        if extra_ms is not None:
            parts.append(f"ms={extra_ms:.1f}")
        if quick_confidence is not None:
            parts.append(f"qc={quick_confidence:.2f}")
        mc.record_feature_usage(
            tenant_id=tenant_id,
            feature="intent_classifier",
            endpoint="|".join(parts),
        )
    except Exception:
        pass


class IntentClassifier:
    """
    Classifies user intent for correct routing.

    Intent types:
    - question: Direct question
    - explanation: Request for explanation
    - summary: Request for summary
    - comparison: Comparing multiple things
    - definition: Asking for definition
    - how_to: Step-by-step instructions
    - analysis: Deep analysis request
    - creation: Content generation request
    - general: General conversation
    """

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    async def classify_intent(
        self,
        query: str,
        conversation_history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Classify user intent.

        Args:
            query: User query
            conversation_history: Optional conversation history

        Returns:
            Dict with:
            - intent: UserIntent enum value
            - confidence: Confidence score (0.0 to 1.0)
            - reasoning: Optional reasoning
        """
        if not query:
            return {
                "intent": UserIntent.GENERAL,
                "confidence": 0.5,
                "reasoning": "Empty query",
            }

        quick_intent = self._quick_classify(query)
        if quick_intent["confidence"] > QUICK_CONFIDENCE_THRESHOLD:
            _record_intent_path(
                self.tenant_id,
                "rule",
                quick_confidence=float(quick_intent["confidence"]),
            )
            return quick_intent

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
            context_block = "Conversation context:\n" + history_context + "\n\n"

        prompt = f"""Classify the user's intent from this query.

Query: {query}
{context_block}
Intent types:
- question: Direct question (What is X? Who did Y?)
- explanation: Request explanation (Explain X, Tell me about Y)
- summary: Request summary (Summarize, Give me an overview)
- whole_document_summary: User wants a summary of the ENTIRE document/PDF/book/chapter using all material (not a short excerpt). Phrases like: summarize the whole document, entire PDF, full file, complete book, all chapters.
- comparison: Comparing things (Compare X and Y, Difference between)
- definition: Asking for definition (What is X, Define Y)
- how_to: Step-by-step instructions (How to X, Steps to Y)
- analysis: Deep analysis (Analyze X, Break down Y)
- creation: Content generation (Create quiz, Generate flashcards)
- general: General conversation

Return one JSON object with keys intent, confidence, reasoning (see system instructions)."""

        llm_kwargs: Dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "feature_tag": "intent_classifier",
        }
        if provider == LLMProvider.OPENAI:
            llm_kwargs["response_format"] = {"type": "json_object"}

        try:
            response = await llm_client.generate(
                prompt=prompt,
                system_prompt=_INTENT_SYSTEM_PROMPT,
                temperature=0.1,
                max_tokens=200,
                **llm_kwargs,
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            print(f"[INTENT_CLASSIFIER] Error classifying intent: {e}")
            _record_intent_path(
                self.tenant_id,
                "llm_error",
                extra_ms=elapsed_ms,
                quick_confidence=float(quick_intent["confidence"]),
            )
            return quick_intent

        elapsed_ms = (time.perf_counter() - t0) * 1000
        parsed = _parse_intent_json(response.content.strip() if response.content else "")

        if not parsed:
            _record_intent_path(
                self.tenant_id,
                "llm_fallback_parse",
                extra_ms=elapsed_ms,
                quick_confidence=float(quick_intent["confidence"]),
            )
            return quick_intent

        intent_str = str(parsed.get("intent", "general")).lower().strip()
        intent = _INTENT_MAP.get(intent_str, UserIntent.GENERAL)

        _record_intent_path(
            self.tenant_id,
            "llm_ok",
            extra_ms=elapsed_ms,
            quick_confidence=float(quick_intent["confidence"]),
        )

        return {
            "intent": intent,
            "confidence": float(parsed.get("confidence", 0.7)),
            "reasoning": str(parsed.get("reasoning", "") or ""),
        }

    def _quick_classify(self, query: str) -> Dict[str, Any]:
        """Quick keyword-based classification."""
        query_lower = query.lower()

        # Bibliographic / metadata (author, copyright, publisher) — same retrieval width as factual questions
        if re.search(
            r"\b(author|authors|who wrote|written by|copyright|publisher|byline|title page|citation)\b",
            query_lower,
        ):
            return {
                "intent": UserIntent.QUESTION,
                "confidence": 0.9,
                "reasoning": "Metadata or attribution question",
            }

        # Question patterns
        if any(word in query_lower for word in ["what", "who", "when", "where", "why", "which"]):
            if "?" in query:
                return {
                    "intent": UserIntent.QUESTION,
                    "confidence": 0.9,
                    "reasoning": "Contains question words and question mark",
                }

        # Explanation patterns
        if any(word in query_lower for word in ["explain", "tell me about", "describe", "elaborate"]):
            return {
                "intent": UserIntent.EXPLANATION,
                "confidence": 0.85,
                "reasoning": "Contains explanation request words",
            }

        # Whole-document summary (map-reduce over all chunks)
        if any(
            phrase in query_lower
            for phrase in [
                "whole document",
                "entire document",
                "entire pdf",
                "whole pdf",
                "full pdf",
                "full document",
                "complete document",
                "summarize the pdf",
                "summarize this pdf",
                "summarize the file",
                "summarize this file",
                "summarize the book",
                "entire book",
                "whole book",
                "all chapters",
                "entire chapter",
            ]
        ) and any(w in query_lower for w in ["summar", "overview", "outline", "brief"]):
            return {
                "intent": UserIntent.WHOLE_DOCUMENT_SUMMARY,
                "confidence": 0.88,
                "reasoning": "Whole-document summary phrasing detected",
            }

        # Summary patterns
        if any(word in query_lower for word in ["summarize", "summary", "overview", "brief"]):
            return {
                "intent": UserIntent.SUMMARY,
                "confidence": 0.85,
                "reasoning": "Contains summary request words",
            }

        # Comparison patterns
        if any(word in query_lower for word in ["compare", "difference", "versus", "vs", "contrast"]):
            return {
                "intent": UserIntent.COMPARISON,
                "confidence": 0.9,
                "reasoning": "Contains comparison words",
            }

        # Definition patterns
        if any(word in query_lower for word in ["define", "definition", "what is", "what are"]):
            return {
                "intent": UserIntent.DEFINITION,
                "confidence": 0.85,
                "reasoning": "Contains definition request words",
            }

        # How-to patterns
        if query_lower.startswith("how to") or query_lower.startswith("how do"):
            return {
                "intent": UserIntent.HOW_TO,
                "confidence": 0.9,
                "reasoning": "Starts with how-to pattern",
            }

        # Creation patterns
        if any(word in query_lower for word in ["create", "generate", "make", "build"]):
            return {
                "intent": UserIntent.CREATION,
                "confidence": 0.8,
                "reasoning": "Contains creation words",
            }

        # Default
        return {
            "intent": UserIntent.GENERAL,
            "confidence": 0.5,
            "reasoning": "No clear intent pattern detected",
        }
