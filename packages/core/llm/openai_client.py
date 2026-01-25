"""
OpenAI LLM Client Implementation

Implements LLMClient interface for OpenAI models.
"""

from typing import AsyncGenerator, Optional, Dict, Any, List
import openai
from config.settings import settings
from packages.core.llm._base import LLMClient, LLMResponse, LLMStreamChunk, LLMProvider


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
    
    @property
    def client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            self._client = openai.OpenAI(api_key=self.api_key)
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
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            **kwargs
        )
        
        content = response.choices[0].message.content or ""
        usage = {
            "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
            "completion_tokens": response.usage.completion_tokens if response.usage else None,
            "total_tokens": response.usage.total_tokens if response.usage else None,
        }
        
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
        """Stream responses from OpenAI."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            stream=True,
            **kwargs
        )
        
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield LLMStreamChunk(
                    content=chunk.choices[0].delta.content,
                    done=False,
                    metadata={"finish_reason": chunk.choices[0].finish_reason if chunk.choices[0].finish_reason else None}
                )
        
        yield LLMStreamChunk(content="", done=True)
    
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


