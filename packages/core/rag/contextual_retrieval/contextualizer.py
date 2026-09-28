from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

from config.settings import settings
from packages.core.llm import get_llm_client, get_model_for_task, detect_provider_from_model
from packages.core.llm._base import LLMProvider
from packages.core.prompts import load_prompt
from packages.core.guardrails.cost_manager import get_cost_manager


@dataclass(frozen=True)
class ChunkEnrichment:
    chunk_context: str
    chunk_summary: str
    chunk_type: str
    section_title: str
    concept_hint: str

    def to_metadata(self) -> Dict[str, Any]:
        return {
            "chunk_context": self.chunk_context,
            "chunk_summary": self.chunk_summary,
            "chunk_type": self.chunk_type,
            "section_title": self.section_title,
            "concept_hint": self.concept_hint,
        }


def _clean_text(s: str) -> str:
    return " ".join((s or "").strip().split())


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    t = (text or "").strip()
    if not t:
        return None
    try:
        obj = json.loads(t)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass
    m = re.search(r"\{.*\}", t, re.DOTALL)
    if not m:
        return None
    try:
        obj = json.loads(m.group())
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def _cap_chars(s: str, max_chars: int) -> str:
    if not s:
        return ""
    if len(s) <= max_chars:
        return s
    return s[: max(0, max_chars - 3)] + "..."


class ChunkContextualizer:
    """
    Ingestion-time contextual chunk enrichment (OpenAI).

    Production guardrails:
    - bounded input sizes (document + chunk)
    - bounded retries
    - safe fallback (caller decides how to proceed)
    """

    def __init__(self, tenant_id: str, user_id: Optional[str] = None):
        self.tenant_id = tenant_id
        self.user_id = user_id

    async def enrich_chunk(
        self,
        *,
        whole_document: str,
        chunk_content: str,
        feature_tag: str = "chunk_contextualization",
        llm_model: Optional[str] = None,
        request_id: Optional[str] = None,
        usage_accumulator: Optional[Dict[str, Any]] = None,
    ) -> Optional[ChunkEnrichment]:
        if not (whole_document or "").strip() or not (chunk_content or "").strip():
            return None

        # Hard caps to protect cost and latency.
        doc_max = int(getattr(settings, "CONTEXTUAL_RETRIEVAL_MAX_DOC_CONTEXT_CHARS", 24000))
        chunk_max = int(getattr(settings, "CONTEXTUAL_RETRIEVAL_MAX_CHUNK_CHARS_FOR_PROMPT", 3500))
        whole_document = _cap_chars(whole_document.strip(), doc_max)
        chunk_content = _cap_chars(chunk_content.strip(), chunk_max)

        target_context_tokens = int(getattr(settings, "CONTEXTUAL_RETRIEVAL_TARGET_CONTEXT_TOKENS", 50))
        target_summary_tokens = int(getattr(settings, "CONTEXTUAL_RETRIEVAL_TARGET_SUMMARY_TOKENS", 50))
        target_concept_terms = int(getattr(settings, "CONTEXTUAL_RETRIEVAL_TARGET_CONCEPT_HINT_TERMS", 8))

        prompt = load_prompt(
            "rag/chunk_contextualization.j2",
            whole_document=whole_document,
            chunk_content=chunk_content,
            target_context_tokens=target_context_tokens,
            target_summary_tokens=target_summary_tokens,
            target_concept_terms=target_concept_terms,
        )

        if llm_model:
            provider, model = detect_provider_from_model(llm_model), llm_model
        else:
            provider, model = get_model_for_task("chunk_contextualization")
        llm = get_llm_client(provider=provider, model=model, temperature=0.2)

        llm_kwargs: Dict[str, Any] = {
            "tenant_id": str(self.tenant_id),
            "user_id": self.user_id,
            "feature_tag": feature_tag,
            # Keep this small; we only need a compact JSON object.
            "max_tokens": 320,
        }
        if request_id:
            llm_kwargs["request_id"] = request_id
        if provider in (LLMProvider.OPENAI, LLMProvider.GROQ):
            llm_kwargs["response_format"] = {"type": "json_object"}

        retries = max(1, int(getattr(settings, "CONTEXTUAL_RETRIEVAL_MAX_RETRIES", 2)))
        last: Optional[Dict[str, Any]] = None
        for attempt in range(retries):
            try:
                resp = await llm.generate(
                    prompt=prompt,
                    system_prompt="Return JSON only. Do not include markdown fences.",
                    temperature=0.2,
                    **llm_kwargs,
                )
                if usage_accumulator is not None and getattr(resp, "usage", None):
                    u = resp.usage or {}
                    pt = int(u.get("prompt_tokens") or 0)
                    ct = int(u.get("completion_tokens") or 0)
                    usage_accumulator["context_llm_prompt_tokens"] = (
                        int(usage_accumulator.get("context_llm_prompt_tokens", 0)) + pt
                    )
                    usage_accumulator["context_llm_completion_tokens"] = (
                        int(usage_accumulator.get("context_llm_completion_tokens", 0)) + ct
                    )
                    cm = get_cost_manager()
                    usage_accumulator["context_llm_cost_usd"] = float(
                        usage_accumulator.get("context_llm_cost_usd", 0.0)
                    ) + float(cm.calculate_cost(model, pt, ct))

                obj = _extract_json(resp.content or "")
                if obj:
                    last = obj
                    # Validate required keys and coerce to strings.
                    out = ChunkEnrichment(
                        chunk_context=_clean_text(str(obj.get("chunk_context", "") or "")),
                        chunk_summary=_clean_text(str(obj.get("chunk_summary", "") or "")),
                        chunk_type=_clean_text(str(obj.get("chunk_type", "") or "")),
                        section_title=_clean_text(str(obj.get("section_title", "") or "")),
                        concept_hint=_clean_text(str(obj.get("concept_hint", "") or "")),
                    )
                    # Require at least some useful signal.
                    if out.chunk_context or out.chunk_summary or out.concept_hint:
                        return out
            except Exception:
                # backoff before retry
                await asyncio.sleep(0.25 * (2**attempt))
                continue

        # best-effort parse if we got something unusable
        if last:
            try:
                out = ChunkEnrichment(
                    chunk_context=_clean_text(str(last.get("chunk_context", "") or "")),
                    chunk_summary=_clean_text(str(last.get("chunk_summary", "") or "")),
                    chunk_type=_clean_text(str(last.get("chunk_type", "") or "")),
                    section_title=_clean_text(str(last.get("section_title", "") or "")),
                    concept_hint=_clean_text(str(last.get("concept_hint", "") or "")),
                )
                if out.chunk_context or out.chunk_summary or out.concept_hint:
                    return out
            except Exception:
                return None

        return None

