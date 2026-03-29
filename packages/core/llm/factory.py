"""
LLM Client Factory

Factory pattern for creating LLM clients based on provider and model.
Enables easy model switching without changing business logic.
"""

from typing import Optional
from enum import Enum
from config.settings import settings
from packages.core.llm._base import LLMClient, LLMProvider
from packages.core.llm.openai_client import OpenAIClient


class LLMModel(str, Enum):
    """Supported models across all providers."""
    # OpenAI Models
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4O = "gpt-4o"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_3_5_TURBO = "gpt-3.5-turbo"

    # Claude Models (future)
    CLAUDE_3_OPUS = "claude-3-opus"
    CLAUDE_3_SONNET = "claude-3-sonnet"
    CLAUDE_3_HAIKU = "claude-3-haiku"


def get_llm_client(
    provider: Optional[LLMProvider] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None
) -> LLMClient:
    """
    Factory function to create LLM clients.
    
    Args:
        provider: LLM provider (if None, auto-detect from model)
        model: Model name (if None, use default for provider)
        temperature: Temperature setting
        max_tokens: Max tokens setting
        
    Returns:
        LLMClient instance
        
    Raises:
        ValueError: If provider/model combination is invalid
    """
    # Auto-detect provider from model if not specified
    if provider is None and model:
        provider = _detect_provider_from_model(model)
    elif provider is None:
        # Default to OpenAI
        provider = LLMProvider.OPENAI
    
    # Set default model if not specified
    if model is None:
        model = _get_default_model(provider)
    
    # Create client based on provider
    if provider == LLMProvider.OPENAI:
        return OpenAIClient(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
    elif provider == LLMProvider.GEMINI:
        raise ValueError(
            "Gemini provider is disabled in this codebase. "
            "Update your routing to use OpenAI models only."
        )
    elif provider == LLMProvider.CLAUDE:
        # Future: ClaudeClient
        raise ValueError(f"Claude provider not yet implemented")
    else:
        raise ValueError(f"Unknown provider: {provider}")


def _detect_provider_from_model(model: str) -> LLMProvider:
    """Detect provider from model name."""
    model_lower = model.lower()
    
    if model_lower.startswith("gpt") or "openai" in model_lower:
        return LLMProvider.OPENAI
    elif "claude" in model_lower:
        return LLMProvider.CLAUDE
    else:
        # Default to OpenAI for unknown models
        return LLMProvider.OPENAI


def _get_default_model(provider: LLMProvider) -> str:
    """Get default model for provider."""
    defaults = {
        LLMProvider.OPENAI: LLMModel.GPT_4O_MINI.value,
        LLMProvider.CLAUDE: LLMModel.CLAUDE_3_HAIKU.value,
    }
    return defaults.get(provider, LLMModel.GPT_4O_MINI.value)


def get_model_for_task(task_type: str) -> tuple:
    """
    Get recommended provider and model for a specific task type.
    
    Args:
        task_type: Task type (quiz, chat, report, etc.)
        
    Returns:
        Tuple of (provider, model)
    """
    # Task-based routing (can be configured via settings)
    task_routing = {
        # Studio structured tasks -> OpenAI (better JSON adherence)
        "quiz": (LLMProvider.OPENAI, LLMModel.GPT_4O_MINI.value),
        "flashcards": (LLMProvider.OPENAI, LLMModel.GPT_4O_MINI.value),
        "mind_map": (LLMProvider.OPENAI, LLMModel.GPT_4O_MINI.value),
        "slide_deck": (LLMProvider.OPENAI, LLMModel.GPT_4O_MINI.value),
        "intent_classifier": (LLMProvider.OPENAI, LLMModel.GPT_4O_MINI.value),
        "query_rewriter": (LLMProvider.OPENAI, LLMModel.GPT_4O_MINI.value),
        "scope_narrower": (LLMProvider.OPENAI, LLMModel.GPT_4O_MINI.value),

        # Content-heavy Studio tasks -> OpenAI as well
        # Use gpt-4o for better long-form quality; keep chat on gpt-4o-mini for cost/latency.
        "report": (LLMProvider.OPENAI, LLMModel.GPT_4O.value),
        "infographic": (LLMProvider.OPENAI, LLMModel.GPT_4O.value),

        # Chat -> OpenAI
        "chat": (LLMProvider.OPENAI, LLMModel.GPT_4O_MINI.value),
        
    }
    
    return task_routing.get(task_type, (LLMProvider.OPENAI, LLMModel.GPT_4O_MINI.value))


