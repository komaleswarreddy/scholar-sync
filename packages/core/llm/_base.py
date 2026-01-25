"""
Base LLM Client Interface

Abstract base class that all LLM providers must implement.
This ensures consistent interface across different providers.

Internal base class - use LLMClient from __init__.py
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    GEMINI = "gemini"
    CLAUDE = "claude"  # Future support


@dataclass
class LLMResponse:
    """Standardized LLM response."""
    content: str
    model: str
    provider: str
    usage: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class LLMStreamChunk:
    """Streaming response chunk."""
    content: str
    done: bool = False
    metadata: Optional[Dict[str, Any]] = None


class LLMClient(ABC):
    """
    Abstract base class for LLM clients.
    
    All LLM providers must implement this interface to ensure
    consistent behavior across different vendors.
    """
    
    def __init__(self, model: str, temperature: float = 0.7, max_tokens: Optional[int] = None):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.provider = self._get_provider()
    
    @abstractmethod
    def _get_provider(self) -> LLMProvider:
        """Return the provider type."""
        pass
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a single response from the LLM.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            **kwargs: Provider-specific parameters
            
        Returns:
            LLMResponse with standardized format
        """
        pass
    
    @abstractmethod
    async def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """
        Stream responses from the LLM.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            **kwargs: Provider-specific parameters
            
        Yields:
            LLMStreamChunk objects
        """
        pass
    
    @abstractmethod
    async def generate_batch(
        self,
        prompts: List[str],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> List[LLMResponse]:
        """
        Generate responses for multiple prompts (if supported).
        
        Args:
            prompts: List of prompts
            system_prompt: Optional system prompt
            **kwargs: Provider-specific parameters
            
        Returns:
            List of LLMResponse objects
        """
        pass
    
    def validate_response(self, response: LLMResponse) -> bool:
        """
        Validate response format (can be overridden by subclasses).
        
        Args:
            response: Response to validate
            
        Returns:
            True if valid, False otherwise
        """
        return bool(response.content and response.content.strip())


