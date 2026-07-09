"""
OpenAI LLM Client Implementation

Implements LLMClient interface for OpenAI models.
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


class OpenAIClient(LLMClient):
    """OpenAI implementation of LLMClient."""
    
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        api_key: Optional[str] = None
    ):
        super().__init__(model, temperature, max_tokens)
        self.api_key = api_key or settings.OPENAI_API_KEY
        if not self.api_key or self.api_key == "your-openai-api-key":
            raise ValueError("OpenAI API key not configured. Please set OPENAI_API_KEY in .env")
        self._client = None
        self._async_client = None

    @property
    def async_client(self):
        """Lazy initialization of the async OpenAI client (used by stream_generate).

        Mirrors `client` below: an explicit httpx.AsyncClient avoids the same
        OpenAI/httpx 'proxies' kwarg incompatibility as the sync client.
        """
        if self._async_client is None:
            try:
                if httpx is not None:
                    http_client = httpx.AsyncClient(timeout=200.0)
                    self._async_client = openai.AsyncOpenAI(
                        api_key=self.api_key,
                        http_client=http_client,
                    )
                else:
                    self._async_client = openai.AsyncOpenAI(api_key=self.api_key)
            except Exception as e:
                if 'proxies' in str(e).lower():
                    self._async_client = openai.AsyncOpenAI(api_key=self.api_key)
                else:
                    raise
        return self._async_client

    @property
    def client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            # Workaround for OpenAI 1.9.0/1.10.0 bug with httpx proxies parameter
            # Create a custom httpx client without proxies to avoid the compatibility issue
            try:
                if httpx is not None:
                    # Create httpx client explicitly (without proxies) and pass to OpenAI
                    # This bypasses OpenAI's internal client creation that tries to pass 'proxies'
                    # Timeout widened to 200s: the frontend budgets up to 180s for long-running
                    # studio generations (mind_map/slide_deck) via this same shared client
                    # (see apps/web/src/lib/api-client.ts). A 60s backend timeout was causing
                    # legitimate long generations to fail before the frontend gave up.
                    http_client = httpx.Client(timeout=200.0)
                    self._client = openai.OpenAI(
                        api_key=self.api_key,
                        http_client=http_client,
                    )
                else:
                    # Fallback: try without custom http_client
                    self._client = openai.OpenAI(api_key=self.api_key)
            except Exception as e:
                # If custom client fails, try standard initialization
                if 'proxies' in str(e).lower():
                    # Last resort: try standard initialization
                    self._client = openai.OpenAI(api_key=self.api_key)
                else:
                    raise
        return self._client
    
    def _get_provider(self) -> LLMProvider:
        return LLMProvider.OPENAI
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a response using OpenAI."""
        # Extract metrics context from kwargs
        tenant_id = kwargs.pop("tenant_id", None)
        user_id = kwargs.pop("user_id", None)
        feature_tag = kwargs.pop("feature_tag", None)
        request_id = kwargs.pop("request_id", None)
        # Back-compat: older callers pass `feature=...`
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

        # Sync OpenAI client blocks the asyncio event loop; offload so other requests
        # (e.g. admin health / DB checks during long ingests) can still run.
        call_api = functools.partial(
            self.client.chat.completions.create,
            model=self.model,
            messages=messages,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            **kwargs,
        )
        response = await asyncio.to_thread(call_api)

        latency_ms = (time.time() - start_time) * 1000
        
        content = response.choices[0].message.content or ""
        # Some OpenAI-compatible endpoints/proxies return `usage` as a plain
        # dict instead of the SDK's attribute-style object.
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

        # Record metrics when tenant is known (user_id optional for legacy callers; prefer passing user_id)
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
            metadata={"finish_reason": response.choices[0].finish_reason}
        )
    
    async def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """Stream responses from OpenAI using the async client.

        Uses `openai.AsyncOpenAI` (not the sync client iterated with a plain `for`
        loop) so each network read yields the event loop instead of blocking it —
        important now that this is on the primary chat request path, not just a
        one-off test script, and multiple tenants' streams run concurrently on the
        same worker.
        """
        tenant_id = kwargs.pop("tenant_id", None)
        user_id = kwargs.pop("user_id", None)
        feature_tag = kwargs.pop("feature_tag", None)
        request_id = kwargs.pop("request_id", None)
        # Back-compat: older callers pass `feature=...` (not supported by OpenAI API)
        feature = kwargs.pop("feature", None)
        if feature and not feature_tag:
            feature_tag = str(feature)
        kwargs.pop("stream", None)  # streaming is controlled internally below

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
            # Ask the API to include a final usage-only chunk so cost/token tracking
            # stays accurate for streamed calls (not just estimated from characters).
            stream = await self.async_client.chat.completions.create(
                extra_body={"stream_options": {"include_usage": True}},
                **create_kwargs,
            )
        except Exception:
            # Older API/account combinations may reject `stream_options`; retry once
            # without it. No tokens have been generated yet at this point, so this is
            # a plain retry, not a duplicate/partial generation.
            stream = await self.async_client.chat.completions.create(**create_kwargs)

        finish_reason: Optional[str] = None
        usage_payload: Optional[Dict[str, Any]] = None
        completion_chars = 0

        async for chunk in stream:
            chunk_usage = getattr(chunk, "usage", None)
            if chunk_usage:
                # Some OpenAI-compatible endpoints/proxies (and mocked test
                # clients) return `usage` as a plain dict instead of the SDK's
                # attribute-style object, so support both shapes.
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
            # Fallback estimate (same heuristic used for pre-flight budget checks
            # above) when the API/SDK combination did not return stream usage.
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
        **kwargs
    ) -> List[LLMResponse]:
        """Generate responses for multiple prompts."""
        # OpenAI doesn't natively support batch, so we'll do sequential
        # In production, you might want to use asyncio.gather for parallel requests
        responses = []
        for prompt in prompts:
            response = await self.generate(prompt, system_prompt, **kwargs)
            responses.append(response)
        return responses


