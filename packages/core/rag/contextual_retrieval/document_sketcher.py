from __future__ import annotations

import json
from typing import Any, Dict, Optional

from config.settings import settings
from packages.core.llm import get_llm_client
from packages.core.llm._base import LLMProvider
from packages.core.prompts import load_prompt
from packages.core.guardrails.cost_manager import get_cost_manager
from packages.core.llm.factory import get_model_for_task


def _cap_chars(s: str, max_chars: int) -> str:
    if not s:
        return ""
    if len(s) <= max_chars:
        return s
    return s[: max(0, max_chars - 3)] + "..."


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    t = (text or "").strip()
    if not t:
        return None
    try:
        obj = json.loads(t)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


async def generate_ncert_document_sketch(
    *,
    tenant_id: str,
    user_id: Optional[str],
    header: str,
    document_text: str,
    model: str,
    request_id: Optional[str] = None,
    usage_accumulator: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    max_in = int(getattr(settings, "CONTEXTUAL_RETRIEVAL_NCERT_DOC_SKETCH_MAX_INPUT_CHARS", 12000))
    max_out_tokens = int(
        getattr(settings, "CONTEXTUAL_RETRIEVAL_NCERT_DOC_SKETCH_MAX_OUTPUT_TOKENS", 700)
    )
    max_chars = int(getattr(settings, "CONTEXTUAL_RETRIEVAL_NCERT_DOC_SKETCH_MAX_CHARS", 3500))

    header = _cap_chars((header or "").strip(), 700)
    document_text = _cap_chars((document_text or "").strip(), max_in)

    prompt = load_prompt(
        "rag/ncert_document_sketch.j2",
        header=header,
        document_text=document_text,
    )
    llm = get_llm_client(provider=LLMProvider.OPENAI, model=model, temperature=0.2)

    resp = await llm.generate(
        prompt=prompt,
        system_prompt="Return JSON only. Do not include markdown fences.",
        tenant_id=str(tenant_id),
        user_id=user_id,
        feature_tag="ncert_global_doc_sketch",
        request_id=request_id,
        max_tokens=max_out_tokens,
        response_format={"type": "json_object"},
        temperature=0.2,
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
    if not obj:
        return None

    # Final safety cap
    try:
        s = json.dumps(obj, ensure_ascii=False)
        if len(s) > max_chars:
            # Keep only the most important keys if it got too large
            obj = {
                "chapter_title": obj.get("chapter_title", ""),
                "main_sections": obj.get("main_sections", []),
                "key_definitions": obj.get("key_definitions", {}),
                "concepts": obj.get("concepts", []),
            }
    except Exception:
        pass

    return obj


def _resolve_upload_sketch_model(explicit: str) -> str:
    m = (explicit or "").strip()
    if m:
        return m
    _, task_model = get_model_for_task("chunk_contextualization")
    return str(task_model)


async def generate_upload_document_sketch(
    *,
    tenant_id: str,
    user_id: Optional[str],
    header: str,
    document_text: str,
    model: str,
    request_id: Optional[str] = None,
    usage_accumulator: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    One-time compact sketch for normal tenant uploads (same JSON shape as NCERT sketch for reuse in prompts).
    """
    max_in = int(getattr(settings, "CONTEXTUAL_RETRIEVAL_DOC_SKETCH_MAX_INPUT_CHARS", 12000))
    max_out_tokens = int(
        getattr(settings, "CONTEXTUAL_RETRIEVAL_DOC_SKETCH_MAX_OUTPUT_TOKENS", 700)
    )
    max_chars = int(getattr(settings, "CONTEXTUAL_RETRIEVAL_DOC_SKETCH_MAX_CHARS", 3500))
    resolved_model = _resolve_upload_sketch_model(model)

    header = _cap_chars((header or "").strip(), 700)
    document_text = _cap_chars((document_text or "").strip(), max_in)

    prompt = load_prompt(
        "rag/document_sketch.j2",
        header=header,
        document_text=document_text,
    )
    llm = get_llm_client(provider=LLMProvider.OPENAI, model=resolved_model, temperature=0.2)

    resp = await llm.generate(
        prompt=prompt,
        system_prompt="Return JSON only. Do not include markdown fences.",
        tenant_id=str(tenant_id),
        user_id=user_id,
        feature_tag="normal_upload_doc_sketch",
        request_id=request_id,
        max_tokens=max_out_tokens,
        response_format={"type": "json_object"},
        temperature=0.2,
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
        ) + float(cm.calculate_cost(resolved_model, pt, ct))

    obj = _extract_json(resp.content or "")
    if not obj:
        return None

    try:
        s = json.dumps(obj, ensure_ascii=False)
        if len(s) > max_chars:
            obj = {
                "chapter_title": obj.get("chapter_title", ""),
                "main_sections": obj.get("main_sections", []),
                "key_definitions": obj.get("key_definitions", {}),
                "concepts": obj.get("concepts", []),
            }
    except Exception:
        pass

    return obj

