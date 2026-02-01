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
from packages.core.llm.gemini_client import GeminiClient


class LLMModel(str, Enum):
    """Supported models across all providers."""
    # OpenAI Models
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4O = "gpt-4o"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    
    # Gemini Models
    # NOTE: gemini-1.5-flash has been RETIRED by Google - auto-upgrades to gemini-2.0-flash-exp
    GEMINI_1_5_FLASH = "gemini-1.5-flash"  # RETIRED - Auto-upgrades to GEMINI_2_0_FLASH_EXP (kept for backward compatibility)
    GEMINI_2_0_FLASH_EXP = "gemini-2.0-flash-exp"  # Recommended: Experimental, newer model (works with v1 API)
    GEMINI_2_5_FLASH = "gemini-2.5-flash"  # Recommended: Stable newer model (works with v1 API)
    GEMINI_1_5_PRO = "gemini-1.5-pro"  # Alternative: Pro version (more compatible)
    
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
    
    # Intercept retired gemini-1.5-flash model and replace immediately
    # This model has been retired by Google and is not available in v1beta API
    if model == "gemini-1.5-flash" or (isinstance(model, str) and "1.5-flash" in model.lower()):
        print(f"[WARNING] [FACTORY] Model 'gemini-1.5-flash' has been retired by Google. Auto-upgrading to 'gemini-pro'")
        model = "gemini-pro"
    
    # Create client based on provider
    if provider == LLMProvider.OPENAI:
        return OpenAIClient(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
    elif provider == LLMProvider.GEMINI:
        return GeminiClient(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
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
    elif "gemini" in model_lower:
        return LLMProvider.GEMINI
    elif "claude" in model_lower:
        return LLMProvider.CLAUDE
    else:
        # Default to OpenAI for unknown models
        return LLMProvider.OPENAI


def _get_default_model(provider: LLMProvider) -> str:
    """Get default model for provider."""
    defaults = {
        LLMProvider.OPENAI: LLMModel.GPT_4O_MINI.value,
        # Use gemini-pro as default (most compatible with v1beta API)
        LLMProvider.GEMINI: "gemini-pro",
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
        # Structured tasks -> OpenAI (better JSON adherence)
        "quiz": (LLMProvider.OPENAI, LLMModel.GPT_4O_MINI.value),
        "flashcards": (LLMProvider.OPENAI, LLMModel.GPT_4O_MINI.value),
        "mind_map": (LLMProvider.OPENAI, LLMModel.GPT_4O_MINI.value),
        "slide_deck": (LLMProvider.OPENAI, LLMModel.GPT_4O_MINI.value),
        
        # Content-heavy tasks -> Gemini (larger context window)
        # Use gemini-pro (most compatible with v1beta API)
        "report": (LLMProvider.GEMINI, "gemini-pro"),
        "infographic": (LLMProvider.GEMINI, "gemini-pro"),
        
        # Chat -> Gemini (better for conversational)
        # Use gemini-pro (most compatible with v1beta API)
        "chat": (LLMProvider.GEMINI, "gemini-pro"),
    }
    
    return task_routing.get(task_type, (LLMProvider.OPENAI, LLMModel.GPT_4O_MINI.value))


