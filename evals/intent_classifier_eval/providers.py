"""Multi-provider LLM caller for intent classifier evals (eval-only, not production).

Supports optional streaming so the harness can record Time-To-First-Token (TTFT).
When an ``on_first_token`` callback is supplied, the provider streams the response
and invokes the callback exactly once, the moment the first content token arrives.
On any streaming failure it falls back to a plain non-streaming request.
"""

from __future__ import annotations

import json
import logging
import os
import random
import time
from typing import Any, Callable, Dict, Optional, Union

import requests

logger = logging.getLogger(__name__)

_TIMEOUT = int(os.environ.get("INTENT_EVAL_TIMEOUT", "120"))


def _request_timeout(max_tokens: int) -> int:
    """Scale HTTP read timeout for long coach_json generations."""
    return max(_TIMEOUT, 120 + max_tokens // 25)
_EMPTY_USAGE: Dict[str, int] = {
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0,
}

# Retry transient rate-limit / overload errors with exponential backoff + jitter.
_MAX_RETRIES = int(os.environ.get("INTENT_EVAL_MAX_RETRIES", "5"))
_BASE_BACKOFF = float(os.environ.get("INTENT_EVAL_BACKOFF_SECONDS", "2.0"))
# Optional fixed delay before every call to proactively smooth request bursts
# (helps stay under provider per-minute limits). 0 = disabled.
_THROTTLE_SECONDS = float(os.environ.get("INTENT_EVAL_THROTTLE_SECONDS", "0"))
_RETRYABLE_MARKERS = (
    "429",
    "rate limit",
    "rate_limit",
    "ratelimit",
    "too many requests",
    "overloaded",
    "503",
    "resource_exhausted",
    "resource exhausted",
    "quota",
    "capacity",
    "try again",
)

OnFirstToken = Optional[Callable[[], None]]

_EMPTY_META: Dict[str, Any] = {
    "refusal": None,
    "finish_reason": None,
}


def _is_gpt5_family(model: str) -> bool:
    m = (model or "").lower()
    return "gpt-5" in m or m.startswith("o")


def _normalize_llm_result(
    text: str,
    usage: Dict[str, int],
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    meta = meta or _EMPTY_META
    return {
        "text": text or "",
        "usage": usage or dict(_EMPTY_USAGE),
        "refusal": meta.get("refusal"),
        "finish_reason": meta.get("finish_reason"),
    }


def _is_retryable(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(marker in msg for marker in _RETRYABLE_MARKERS)


def call_model(
    *,
    provider: str,
    model: str,
    system: str,
    user: str,
    temperature: float = 0.1,
    max_tokens: int = 400,
    json_mode: bool = False,
    return_usage: bool = False,
    on_first_token: OnFirstToken = None,
) -> Union[str, Dict[str, Any]]:
    """
    Call an LLM and return raw text (or {text, usage} when return_usage=True).
    Never raises — returns empty string / zero usage on failure.

    When ``on_first_token`` is provided the call streams and fires the callback
    on the first content token (used to capture TTFT). Falls back to a
    non-streaming request if streaming errors out.
    """
    provider = (provider or "openai").lower().strip()
    text, usage, meta = "", dict(_EMPTY_USAGE), dict(_EMPTY_META)

    def _dispatch() -> Any:
        if provider == "openai":
            return _call_openai(
                model, system, user, temperature, max_tokens, on_first_token, json_mode
            )
        if provider in ("anthropic", "claude"):
            t, u = _call_anthropic(
                model, system, user, temperature, max_tokens, on_first_token
            )
            return t, u, dict(_EMPTY_META)
        if provider in ("gemini", "google"):
            t, u = _call_gemini(
                model, system, user, temperature, max_tokens, on_first_token
            )
            return t, u, dict(_EMPTY_META)
        logger.warning("Unknown provider %s", provider)
        return "", dict(_EMPTY_USAGE), dict(_EMPTY_META)

    if _THROTTLE_SECONDS > 0:
        time.sleep(_THROTTLE_SECONDS)

    for attempt in range(_MAX_RETRIES + 1):
        try:
            text, usage, meta = _dispatch()
            break
        except Exception as exc:
            if attempt < _MAX_RETRIES and _is_retryable(exc):
                delay = _BASE_BACKOFF * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(
                    "Rate-limited (provider=%s model=%s attempt=%d/%d): %s — retrying in %.1fs",
                    provider, model, attempt + 1, _MAX_RETRIES, str(exc)[:160], delay,
                )
                time.sleep(delay)
                continue
            logger.warning("call_model failed provider=%s model=%s: %s", provider, model, exc)
            text, usage, meta = "", dict(_EMPTY_USAGE), dict(_EMPTY_META)
            break

    if return_usage:
        return _normalize_llm_result(text, usage, meta)
    return text


def _fire_once(cb: OnFirstToken, fired: Dict[str, bool]) -> None:
    """Invoke the first-token callback at most once."""
    if cb is not None and not fired.get("done"):
        fired["done"] = True
        try:
            cb()
        except Exception:
            pass


def _iter_sse(resp: requests.Response):
    """Yield ``data:`` payload strings from a Server-Sent-Events stream."""
    for raw in resp.iter_lines(decode_unicode=True):
        if not raw:
            continue
        line = raw.strip()
        if line.startswith("data:"):
            yield line[len("data:"):].strip()


# --------------------------------------------------------------------------- #
# OpenAI
# --------------------------------------------------------------------------- #
def _supports_custom_temperature(model: str) -> bool:
    """gpt-5 family and o-series reasoning models only allow the default temperature (1)."""
    return not _is_gpt5_family(model)


def _extract_openai_choice(data: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
    """Read content, refusal, and finish_reason from a chat-completions response."""
    choice = (data.get("choices") or [{}])[0] or {}
    message = choice.get("message") or {}
    content = message.get("content")
    text = (content if isinstance(content, str) else "").strip()
    refusal_raw = message.get("refusal")
    refusal = (refusal_raw if isinstance(refusal_raw, str) else "").strip() or None
    finish_reason = choice.get("finish_reason")
    return text, {"refusal": refusal, "finish_reason": finish_reason}


def _openai_payload(
    model: str,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
    json_mode: bool = False,
) -> Dict[str, Any]:
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    use_completion_tokens = _is_gpt5_family(model)
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
    }
    if _supports_custom_temperature(model):
        payload["temperature"] = temperature
    if use_completion_tokens:
        payload["max_completion_tokens"] = max_tokens
        payload["reasoning_effort"] = "low"
    else:
        payload["max_tokens"] = max_tokens
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    elif not model.lower().startswith("o1") and not _is_gpt5_family(model):
        payload["response_format"] = {"type": "json_object"}
    return payload


def _openai_usage(data: Dict[str, Any]) -> Dict[str, int]:
    usage_raw = data.get("usage") or {}
    pt = int(usage_raw.get("prompt_tokens") or 0)
    ct = int(usage_raw.get("completion_tokens") or 0)
    return {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct}


def _post_openai_chat(
    url: str,
    headers: Dict[str, str],
    payload: Dict[str, Any],
) -> requests.Response:
    def _post(body: Dict[str, Any]) -> requests.Response:
        return requests.post(url, headers=headers, json=body, timeout=_TIMEOUT)

    resp = _post(payload)
    if resp.status_code >= 400 and "temperature" in resp.text:
        payload.pop("temperature", None)
        resp = _post(payload)
    if resp.status_code >= 400 and "max_tokens" in resp.text:
        saved = payload.pop("max_tokens", None) or payload.get("max_completion_tokens")
        if saved is not None:
            payload["max_completion_tokens"] = saved
        resp = _post(payload)
    if resp.status_code >= 400 and "reasoning_effort" in resp.text:
        payload.pop("reasoning_effort", None)
        resp = _post(payload)
    if resp.status_code >= 400 and "response_format" in resp.text:
        payload.pop("response_format", None)
        resp = _post(payload)
    return resp


def _call_openai_non_streaming(
    url: str,
    headers: Dict[str, str],
    model: str,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
    json_mode: bool,
    *,
    allow_length_retry: bool = True,
) -> tuple[str, Dict[str, int], Dict[str, Any]]:
    payload = _openai_payload(model, system, user, temperature, max_tokens, json_mode)
    resp = _post_openai_chat(url, headers, payload)
    if resp.status_code >= 400:
        logger.warning("OpenAI error %s: %s", resp.status_code, resp.text[:300])
        return "", dict(_EMPTY_USAGE), dict(_EMPTY_META)

    data = resp.json()
    text, meta = _extract_openai_choice(data)
    usage = _openai_usage(data)

    if not text and meta.get("refusal"):
        logger.info(
            "OpenAI refusal (model=%s finish_reason=%s): %s",
            model,
            meta.get("finish_reason"),
            str(meta.get("refusal"))[:160],
        )
        return text, usage, meta

    if (
        allow_length_retry
        and not text
        and meta.get("finish_reason") == "length"
    ):
        retry_tokens = min(max(max_tokens * 2, 800), 4096)
        if retry_tokens > max_tokens:
            logger.warning(
                "OpenAI finish_reason=length with empty content (model=%s); "
                "retrying with max_completion_tokens=%d",
                model,
                retry_tokens,
            )
            return _call_openai_non_streaming(
                url,
                headers,
                model,
                system,
                user,
                temperature,
                retry_tokens,
                json_mode,
                allow_length_retry=False,
            )

    if (
        allow_length_retry
        and not text
        and not meta.get("refusal")
        and _is_gpt5_family(model)
    ):
        retry_tokens = min(max(max_tokens * 2, 2000), 8192)
        if retry_tokens > max_tokens:
            logger.warning(
                "OpenAI empty content (model=%s finish_reason=%s); "
                "retrying with max_completion_tokens=%d",
                model,
                meta.get("finish_reason"),
                retry_tokens,
            )
            return _call_openai_non_streaming(
                url,
                headers,
                model,
                system,
                user,
                temperature,
                retry_tokens,
                json_mode,
                allow_length_retry=False,
            )

    return text, usage, meta


def _call_openai(
    model: str,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
    on_first_token: OnFirstToken = None,
    json_mode: bool = False,
) -> tuple[str, Dict[str, int], Dict[str, Any]]:
    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not api_key:
        return "", dict(_EMPTY_USAGE), dict(_EMPTY_META)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    url = "https://api.openai.com/v1/chat/completions"

    if on_first_token is not None:
        try:
            text, usage, meta = _stream_openai(
                url, headers, model, system, user, temperature, max_tokens, on_first_token, json_mode
            )
            if text.strip() or meta.get("refusal"):
                return text, usage, meta
            logger.info(
                "OpenAI stream returned empty content (model=%s finish_reason=%s); "
                "falling back to non-streaming for metadata/retry",
                model,
                meta.get("finish_reason"),
            )
        except Exception as exc:
            logger.warning("OpenAI stream failed, falling back: %s", exc)

    return _call_openai_non_streaming(
        url, headers, model, system, user, temperature, max_tokens, json_mode
    )


def _stream_openai(
    url: str,
    headers: Dict[str, str],
    model: str,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
    on_first_token: Callable[[], None],
    json_mode: bool = False,
) -> tuple[str, Dict[str, int], Dict[str, Any]]:
    payload = _openai_payload(model, system, user, temperature, max_tokens, json_mode)
    payload["stream"] = True
    payload["stream_options"] = {"include_usage": True}

    fired: Dict[str, bool] = {}
    parts: list[str] = []
    refusal_parts: list[str] = []
    finish_reason: Optional[str] = None
    pt = ct = 0
    with requests.post(url, headers=headers, json=payload, timeout=_TIMEOUT, stream=True) as resp:
        if resp.status_code >= 400:
            raise RuntimeError(f"OpenAI stream HTTP {resp.status_code}: {resp.text[:200]}")
        for data in _iter_sse(resp):
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except Exception:
                continue
            for choice in chunk.get("choices") or []:
                if choice.get("finish_reason"):
                    finish_reason = choice.get("finish_reason")
                delta = choice.get("delta") or {}
                piece = delta.get("content")
                if piece:
                    _fire_once(on_first_token, fired)
                    parts.append(piece)
                refusal_piece = delta.get("refusal")
                if isinstance(refusal_piece, str) and refusal_piece:
                    refusal_parts.append(refusal_piece)
            usage_raw = chunk.get("usage")
            if usage_raw:
                pt = int(usage_raw.get("prompt_tokens") or pt)
                ct = int(usage_raw.get("completion_tokens") or ct)
    text = "".join(parts).strip()
    refusal = "".join(refusal_parts).strip() or None
    meta = {"refusal": refusal, "finish_reason": finish_reason}
    return text, {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct}, meta


# --------------------------------------------------------------------------- #
# Anthropic
# --------------------------------------------------------------------------- #
def _call_anthropic(
    model: str,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
    on_first_token: OnFirstToken = None,
) -> tuple[str, Dict[str, int]]:
    api_key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if not api_key:
        return "", dict(_EMPTY_USAGE)
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    url = "https://api.anthropic.com/v1/messages"
    body: Dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }

    if on_first_token is not None:
        try:
            return _stream_anthropic(url, headers, body, on_first_token, max_tokens)
        except Exception as exc:
            logger.warning("Anthropic stream failed, falling back: %s", exc)

    resp = requests.post(
        url, headers=headers, json=body, timeout=_request_timeout(max_tokens)
    )
    if resp.status_code >= 400:
        logger.warning("Anthropic error %s: %s", resp.status_code, resp.text[:300])
        return "", dict(_EMPTY_USAGE)
    data = resp.json()
    parts = []
    for block in data.get("content") or []:
        if block.get("type") == "text":
            parts.append(block.get("text", ""))
    text = "\n".join(parts).strip()
    usage_raw = data.get("usage") or {}
    pt = int(usage_raw.get("input_tokens") or 0)
    ct = int(usage_raw.get("output_tokens") or 0)
    return text, {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct}


def _stream_anthropic(
    url: str,
    headers: Dict[str, str],
    body: Dict[str, Any],
    on_first_token: Callable[[], None],
    max_tokens: int = 400,
) -> tuple[str, Dict[str, int]]:
    body = {**body, "stream": True}
    fired: Dict[str, bool] = {}
    parts: list[str] = []
    pt = ct = 0
    with requests.post(
        url,
        headers=headers,
        json=body,
        timeout=_request_timeout(max_tokens),
        stream=True,
    ) as resp:
        if resp.status_code >= 400:
            raise RuntimeError(f"Anthropic stream HTTP {resp.status_code}: {resp.text[:200]}")
        for data in _iter_sse(resp):
            try:
                evt = json.loads(data)
            except Exception:
                continue
            etype = evt.get("type")
            if etype == "message_start":
                usage_raw = (evt.get("message") or {}).get("usage") or {}
                pt = int(usage_raw.get("input_tokens") or pt)
                ct = int(usage_raw.get("output_tokens") or ct)
            elif etype == "content_block_delta":
                delta = evt.get("delta") or {}
                piece = delta.get("text")
                if piece:
                    _fire_once(on_first_token, fired)
                    parts.append(piece)
            elif etype == "message_delta":
                usage_raw = evt.get("usage") or {}
                if usage_raw.get("output_tokens") is not None:
                    ct = int(usage_raw.get("output_tokens"))
    text = "".join(parts).strip()
    return text, {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct}


# --------------------------------------------------------------------------- #
# Gemini
# --------------------------------------------------------------------------- #
def _gemini_body(system: str, user: str, temperature: float, max_tokens: int) -> Dict[str, Any]:
    gen_config: Dict[str, Any] = {
        "temperature": temperature,
        "maxOutputTokens": max(max_tokens, 1024),
        "responseMimeType": "application/json",
        "thinkingConfig": {"thinkingBudget": 0},
    }
    return {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": gen_config,
    }


def _call_gemini(
    model: str,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
    on_first_token: OnFirstToken = None,
) -> tuple[str, Dict[str, int]]:
    api_key = (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or ""
    ).strip()
    if not api_key:
        return "", dict(_EMPTY_USAGE)

    if on_first_token is not None:
        try:
            return _stream_gemini(model, api_key, system, user, temperature, max_tokens, on_first_token)
        except Exception as exc:
            logger.warning("Gemini stream failed, falling back: %s", exc)

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = _gemini_body(system, user, temperature, max_tokens)
    gen_config = body["generationConfig"]

    def _post(payload: Dict[str, Any]) -> requests.Response:
        return requests.post(url, params={"key": api_key}, json=payload, timeout=_TIMEOUT)

    resp = _post(body)
    if resp.status_code >= 400 and "thinking" in resp.text.lower():
        gen_config.pop("thinkingConfig", None)
        gen_config["maxOutputTokens"] = max(max_tokens, 2048)
        resp = _post(body)
    if resp.status_code >= 400 and "responseMimeType" in resp.text:
        gen_config.pop("responseMimeType", None)
        resp = _post(body)
    if resp.status_code >= 400:
        logger.warning("Gemini error %s: %s", resp.status_code, resp.text[:300])
        return "", dict(_EMPTY_USAGE)

    data = resp.json()
    candidates = data.get("candidates") or []
    if not candidates:
        return "", dict(_EMPTY_USAGE)
    parts = candidates[0].get("content", {}).get("parts") or []
    texts = [p.get("text", "") for p in parts if p.get("text")]
    text = "\n".join(texts).strip()
    usage_raw = data.get("usageMetadata") or {}
    pt = int(usage_raw.get("promptTokenCount") or 0)
    ct = int(usage_raw.get("candidatesTokenCount") or 0)
    thoughts = int(usage_raw.get("thoughtsTokenCount") or 0)
    ct += thoughts
    return text, {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct}


def _stream_gemini(
    model: str,
    api_key: str,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
    on_first_token: Callable[[], None],
) -> tuple[str, Dict[str, int]]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent"
    body = _gemini_body(system, user, temperature, max_tokens)

    fired: Dict[str, bool] = {}
    parts: list[str] = []
    pt = ct = thoughts = 0
    with requests.post(
        url, params={"key": api_key, "alt": "sse"}, json=body, timeout=_TIMEOUT, stream=True
    ) as resp:
        if resp.status_code >= 400:
            raise RuntimeError(f"Gemini stream HTTP {resp.status_code}: {resp.text[:200]}")
        for data in _iter_sse(resp):
            try:
                chunk = json.loads(data)
            except Exception:
                continue
            for cand in chunk.get("candidates") or []:
                for part in (cand.get("content") or {}).get("parts") or []:
                    piece = part.get("text")
                    if piece:
                        _fire_once(on_first_token, fired)
                        parts.append(piece)
            usage_raw = chunk.get("usageMetadata") or {}
            if usage_raw:
                pt = int(usage_raw.get("promptTokenCount") or pt)
                ct = int(usage_raw.get("candidatesTokenCount") or ct)
                thoughts = int(usage_raw.get("thoughtsTokenCount") or thoughts)
    text = "".join(parts).strip()
    total_ct = ct + thoughts
    return text, {"prompt_tokens": pt, "completion_tokens": total_ct, "total_tokens": pt + total_ct}


def provider_available(provider: str) -> bool:
    """Check whether API key exists for provider."""
    p = provider.lower()
    if p == "openai":
        return bool((os.environ.get("OPENAI_API_KEY") or "").strip())
    if p in ("anthropic", "claude"):
        return bool((os.environ.get("ANTHROPIC_API_KEY") or "").strip())
    if p in ("gemini", "google"):
        return bool(
            (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()
        )
    return False
