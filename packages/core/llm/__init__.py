"""
LLM Abstraction Layer

Provides a unified interface for all LLM providers (OpenAI, Gemini, Claude, etc.)
Prevents vendor lock-in and enables easy model switching.
"""

from ._base import LLMClient, LLMResponse, LLMStreamChunk
from .openai_client import OpenAIClient
from .gemini_client import GeminiClient
from .factory import get_llm_client, get_model_for_task, LLMProvider, LLMModel

__all__ = [
    'LLMClient',
    'LLMResponse',
    'LLMStreamChunk',
    'OpenAIClient',
    'GeminiClient',
    'get_llm_client',
    'get_model_for_task',
    'LLMProvider',
    'LLMModel',
]


