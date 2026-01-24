"""
Gemini LLM Client Implementation

Implements LLMClient interface for Google Gemini models.
"""

from typing import AsyncGenerator, Optional, Dict, Any, List
import google.generativeai as genai
from app.core.config import settings
from app.core.llm.base import LLMClient, LLMResponse, LLMStreamChunk, LLMProvider


class GeminiClient(LLMClient):
    """Gemini implementation of LLMClient."""
    
    def __init__(
        self,
        model: str = "gemini-1.5-flash",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        api_key: Optional[str] = None
    ):
        super().__init__(model, temperature, max_tokens)
        self.api_key = api_key or settings.GEMINI_API_KEY
        if not self.api_key or self.api_key == "your-gemini-api-key":
            raise ValueError("Gemini API key not configured. Please set GEMINI_API_KEY in .env")
        self._gemini_model = None
        self._configured = False
    
    def _configure(self):
        """Lazy configuration of Gemini API."""
        if not self._configured:
            genai.configure(api_key=self.api_key)
            self._configured = True
    
    @property
    def gemini_model(self):
        """Lazy initialization of Gemini model."""
        if self._gemini_model is None:
            self._configure()
            # Try newer model first, fallback to older
            try:
                self._gemini_model = genai.GenerativeModel(self.model)
            except:
                # Fallback to 1.5-flash if 2.5-flash doesn't exist
                if "2.5" in self.model:
                    self._gemini_model = genai.GenerativeModel("gemini-1.5-flash")
                else:
                    raise
        return self._gemini_model
    
    def _get_provider(self) -> LLMProvider:
        return LLMProvider.GEMINI
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a response using Gemini."""
        # Combine system prompt and user prompt
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        generation_config = {
            "temperature": temperature or self.temperature,
        }
        if max_tokens or self.max_tokens:
            generation_config["max_output_tokens"] = max_tokens or self.max_tokens
        
        # Merge with any additional kwargs
        generation_config.update(kwargs)
        
        response = self.gemini_model.generate_content(
            full_prompt,
            generation_config=generation_config
        )
        
        content = response.text if response.text else ""
        
        # Extract usage info if available
        usage = None
        if hasattr(response, 'usage_metadata'):
            usage = {
                "prompt_tokens": getattr(response.usage_metadata, 'prompt_token_count', None),
                "completion_tokens": getattr(response.usage_metadata, 'completion_token_count', None),
                "total_tokens": getattr(response.usage_metadata, 'total_token_count', None),
            }
        
        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.provider.value,
            usage=usage,
            metadata={"finish_reason": getattr(response, 'finish_reason', None)}
        )
    
    async def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """Stream responses from Gemini."""
        # Combine system prompt and user prompt
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        generation_config = {
            "temperature": temperature or self.temperature,
        }
        if max_tokens or self.max_tokens:
            generation_config["max_output_tokens"] = max_tokens or self.max_tokens
        
        generation_config.update(kwargs)
        
        response = self.gemini_model.generate_content(
            full_prompt,
            generation_config=generation_config,
            stream=True
        )
        
        for chunk in response:
            if chunk.text:
                yield LLMStreamChunk(
                    content=chunk.text,
                    done=False,
                    metadata={"finish_reason": getattr(chunk, 'finish_reason', None)}
                )
        
        yield LLMStreamChunk(content="", done=True)
    
    async def generate_batch(
        self,
        prompts: List[str],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> List[LLMResponse]:
        """Generate responses for multiple prompts."""
        # Gemini doesn't natively support batch, so sequential
        responses = []
        for prompt in prompts:
            response = await self.generate(prompt, system_prompt, **kwargs)
            responses.append(response)
        return responses
