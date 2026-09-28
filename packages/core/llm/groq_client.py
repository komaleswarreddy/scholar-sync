"""
Groq LLM Client Implementation

Implements LLMClient interface for Groq's OpenAI-compatible chat completions API
(LPU inference — used as the primary text-generation provider for chat, RAG,
studio, tutor, and problem-solver tasks). Embeddings, reranking, image
generation, moderation, and vision OCR stay on their existing providers since
Groq does not offer them.

Errors are allowed to propagate as normal exceptions (rate limits, timeouts,
auth failures) — callers already route unhandled exceptions through
`safe_detail()` / the SSE error-event handler, which returns a clean,
production-safe message to the client and logs the full detail server-side.
"""

from typing import AsyncGenerator, Optional, Dict, Any, List
import asyncio
import functools
import openai
import time
try:
    import httpx
except ImportError:
    httpx = None
from config.settings import settings
from packages.core.llm._base import LLMClient, LLMResponse, LLMStreamChunk, LLMProvider
from packages.core.guardrails.cost_manager import get_cost_manager


def _merge_reasoning_effort(extra_body: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Attach the configured reasoning_effort to a request's extra_body, without
    clobbering any other extra_body fields the caller (e.g. stream_options) set."""
    merged = dict(extra_body or {})
    merged.setdefault("reasoning_effort", getattr(settings, "GROQ_REASONING_EFFORT", "low"))
    return merged


class GroqClient(LLMClient):
    """Groq implementation of LLMClient (OpenAI-compatible chat completions endpoint)."""

    def __init__(
        self,
        model: str = "openai/gpt-oss-120b",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        api_key: Optional[str] = None,
    ):
        super().__init__(model, temperature, max_tokens)
        self.api_key = api_key or settings.GROQ_API_KEY
        if not self.api_key:
            raise ValueError("Groq API key not configured. Please set GROQ_API_KEY in .env")
        self.base_url = getattr(settings, "GROQ_BASE_URL", "https://api.groq.com/openai/v1")
        self._client = None
        self._async_client = None

    @property
    def async_client(self):
        """Lazy initialization of the async Groq client (used by stream_generate)."""
        if self._async_client is None:
            if httpx is not None:
                http_client = httpx.AsyncClient(timeout=120.0)
                self._async_client = openai.AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    http_client=http_client,
                )
            else:
                self._async_client = openai.AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._async_client

    @property
    def client(self):
        """Lazy initialization of the sync Groq client."""
        if self._client is None:
            if httpx is not None:
                http_client = httpx.Client(timeout=120.0)
                self._client = openai.OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    http_client=http_client,
                )
            else:
                self._client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def _get_provider(self) -> LLMProvider:
        return LLMProvider.GROQ

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate a response using Groq."""
        tenant_id = kwargs.pop("tenant_id", None)
        user_id = kwargs.pop("user_id", None)
        feature_tag = kwargs.pop("feature_tag", None)
        request_id = kwargs.pop("request_id", None)
        feature = kwargs.pop("feature", None)
        if feature and not feature_tag:
            feature_tag = str(feature)

        if tenant_id and getattr(settings, "ENABLE_BUDGET_ENFORCEMENT", False):
            from packages.core.guardrails.budget_enforcer import BudgetEnforcer

            cost_manager = get_cost_manager()
            est = cost_manager.calculate_cost(
                self.model,
                prompt_tokens=max(1, len(prompt) // 4),
                completion_tokens=max_tokens or self.max_tokens or 512,
            )
            await BudgetEnforcer().enforce_budget(str(tenant_id), estimated_cost=est)

        start_time = time.time()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Sync client blocks the event loop; offload so other requests can proceed.
        call_api = functools.partial(
            self.client.chat.completions.create,
            model=self.model,
            messages=messages,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            extra_body=_merge_reasoning_effort(kwargs.pop("extra_body", None)),
            **kwargs,
        )
        response = await asyncio.to_thread(call_api)

        latency_ms = (time.time() - start_time) * 1000

        content = response.choices[0].message.content or ""
        raw_usage = response.usage
        if isinstance(raw_usage, dict):
            usage_prompt_tokens = raw_usage.get("prompt_tokens")
            usage_completion_tokens = raw_usage.get("completion_tokens")
            usage_total_tokens = raw_usage.get("total_tokens")
        else:
            usage_prompt_tokens = raw_usage.prompt_tokens if raw_usage else None
            usage_completion_tokens = raw_usage.completion_tokens if raw_usage else None
            usage_total_tokens = raw_usage.total_tokens if raw_usage else None
        usage = {
            "prompt_tokens": usage_prompt_tokens,
            "completion_tokens": usage_completion_tokens,
            "total_tokens": usage_total_tokens,
        }

        if tenant_id and raw_usage:
            cost_manager = get_cost_manager()
            await cost_manager.record_usage(
                tenant_id=str(tenant_id),
                user_id=str(user_id) if user_id else "__unknown_user__",
                model=self.model,
                provider=self.provider.value,
                prompt_tokens=usage_prompt_tokens,
                completion_tokens=usage_completion_tokens,
                feature_tag=feature_tag,
                request_id=request_id,
                latency_ms=latency_ms,
            )

        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.provider.value,
            usage=usage,
            metadata={"finish_reason": response.choices[0].finish_reason},
        )

    async def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """Stream responses from Groq using the async client."""
        tenant_id = kwargs.pop("tenant_id", None)
        user_id = kwargs.pop("user_id", None)
        feature_tag = kwargs.pop("feature_tag", None)
        request_id = kwargs.pop("request_id", None)
        feature = kwargs.pop("feature", None)
        if feature and not feature_tag:
            feature_tag = str(feature)
        kwargs.pop("stream", None)

        resolved_max_tokens = max_tokens or self.max_tokens
        resolved_temperature = temperature or self.temperature

        if tenant_id and getattr(settings, "ENABLE_BUDGET_ENFORCEMENT", False):
            from packages.core.guardrails.budget_enforcer import BudgetEnforcer

            cost_manager = get_cost_manager()
            est = cost_manager.calculate_cost(
                self.model,
                prompt_tokens=max(1, len(prompt) // 4),
                completion_tokens=resolved_max_tokens or 512,
            )
            await BudgetEnforcer().enforce_budget(str(tenant_id), estimated_cost=est)

        start_time = time.time()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        create_kwargs = dict(
            model=self.model,
            messages=messages,
            temperature=resolved_temperature,
            max_tokens=resolved_max_tokens,
            stream=True,
            **kwargs,
        )
        try:
            stream = await self.async_client.chat.completions.create(
                extra_body=_merge_reasoning_effort({"stream_options": {"include_usage": True}}),
                **create_kwargs,
            )
        except Exception:
            # Groq (like OpenAI) may reject stream_options on some model/account combos;
            # retry once without it. No tokens generated yet, so this is a plain retry.
            stream = await self.async_client.chat.completions.create(
                extra_body=_merge_reasoning_effort(None),
                **create_kwargs,
            )

        finish_reason: Optional[str] = None
        usage_payload: Optional[Dict[str, Any]] = None
        completion_chars = 0

        async for chunk in stream:
            chunk_usage = getattr(chunk, "usage", None)
            if chunk_usage:
                if isinstance(chunk_usage, dict):
                    usage_payload = {
                        "prompt_tokens": chunk_usage.get("prompt_tokens"),
                        "completion_tokens": chunk_usage.get("completion_tokens"),
                        "total_tokens": chunk_usage.get("total_tokens"),
                    }
                else:
                    usage_payload = {
                        "prompt_tokens": chunk_usage.prompt_tokens,
                        "completion_tokens": chunk_usage.completion_tokens,
                        "total_tokens": chunk_usage.total_tokens,
                    }
            if chunk.choices:
                choice = chunk.choices[0]
                if choice.finish_reason:
                    finish_reason = choice.finish_reason
                delta = choice.delta.content if choice.delta else None
                if delta:
                    completion_chars += len(delta)
                    yield LLMStreamChunk(
                        content=delta,
                        done=False,
                        metadata={"finish_reason": choice.finish_reason},
                    )

        latency_ms = (time.time() - start_time) * 1000

        if not usage_payload:
            usage_payload = {
                "prompt_tokens": max(1, len(prompt) // 4),
                "completion_tokens": max(1, completion_chars // 4),
                "total_tokens": None,
            }

        if tenant_id:
            try:
                cost_manager = get_cost_manager()
                await cost_manager.record_usage(
                    tenant_id=str(tenant_id),
                    user_id=str(user_id) if user_id else "__unknown_user__",
                    model=self.model,
                    provider=self.provider.value,
                    prompt_tokens=usage_payload.get("prompt_tokens") or 0,
                    completion_tokens=usage_payload.get("completion_tokens") or 0,
                    feature_tag=feature_tag,
                    request_id=request_id,
                    latency_ms=latency_ms,
                )
            except Exception:
                pass

        yield LLMStreamChunk(
            content="",
            done=True,
            metadata={"finish_reason": finish_reason, "usage": usage_payload},
        )

    async def generate_batch(
        self,
        prompts: List[str],
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> List[LLMResponse]:
        """Generate responses for multiple prompts (sequential — Groq has no native batch API)."""
        responses = []
        for prompt in prompts:
            response = await self.generate(prompt, system_prompt, **kwargs)
            responses.append(response)
        return responses
