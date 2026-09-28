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
from packages.core.llm.groq_client import GroqClient


class LLMModel(str, Enum):
    """Supported models across all providers."""
    # Groq Models (primary — text generation)
    GPT_OSS_120B = "openai/gpt-oss-120b"

    # OpenAI Models (embeddings/vision/moderation/image-gen call sites; not primary chat)
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4O = "gpt-4o"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_3_5_TURBO = "gpt-3.5-turbo"

    # Claude Models (future)
    CLAUDE_3_OPUS = "claude-3-opus"
    CLAUDE_3_SONNET = "claude-3-sonnet"
    CLAUDE_3_HAIKU = "claude-3-haiku"


# Groq model-name prefixes/substrings that identify a model as Groq-hosted rather
# than a literal OpenAI/Anthropic model. Used to route registry-configured model
# strings (e.g. from config/models.yaml) to the right client.
_GROQ_MODEL_MARKERS = (
    "openai/gpt-oss",
    "llama-3",
    "llama3",
    "meta-llama/",
    "mixtral",
    "qwen",
    "moonshotai/",
    "kimi",
    "gemma2",
    "gemma-2",
    "deepseek-r1-distill",
)


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
        # Default to Groq (primary text-generation provider)
        provider = LLMProvider.GROQ

    # Set default model if not specified
    if model is None:
        model = _get_default_model(provider)

    # Create client based on provider
    if provider == LLMProvider.GROQ:
        return GroqClient(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
    elif provider == LLMProvider.OPENAI:
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


def detect_provider_from_model(model: str) -> LLMProvider:
    """Detect provider from model name. Public — use this instead of assuming a
    provider (e.g. hardcoding OPENAI) whenever `model` came from get_model_for_task()
    or the model_registry, since either can now resolve to a Groq model string."""
    model_lower = model.lower()

    if any(marker in model_lower for marker in _GROQ_MODEL_MARKERS):
        return LLMProvider.GROQ
    elif model_lower.startswith("gpt") or model_lower.startswith("text-embedding") or "dall-e" in model_lower:
        return LLMProvider.OPENAI
    elif "claude" in model_lower:
        return LLMProvider.CLAUDE
    elif "gemini" in model_lower:
        return LLMProvider.GEMINI
    else:
        # Default unknown models to the primary provider (Groq)
        return LLMProvider.GROQ


# Backcompat alias (was private/internal-only name).
_detect_provider_from_model = detect_provider_from_model


def _get_default_model(provider: LLMProvider) -> str:
    """Get default model for provider."""
    defaults = {
        LLMProvider.GROQ: getattr(settings, "PRIMARY_LLM_MODEL", LLMModel.GPT_OSS_120B.value),
        LLMProvider.OPENAI: LLMModel.GPT_4O_MINI.value,
        LLMProvider.CLAUDE: LLMModel.CLAUDE_3_HAIKU.value,
    }
    return defaults.get(provider, LLMModel.GPT_OSS_120B.value)


def get_model_for_task(task_type: str) -> tuple:
    """
    Get recommended provider and model for a specific task type.
    
    Args:
        task_type: Task type (quiz, chat, slide_deck, etc.)
        
    Returns:
        Tuple of (provider, model)
    """
    # Vision tasks need real multimodal input (image_url content parts). Groq's primary
    # model (openai/gpt-oss-120b) is text-only, so these stay on an OpenAI vision model
    # regardless of provider/registry config below.
    VISION_TASKS = {"source_image_ocr", "image_ocr", "diagram_label_ocr"}
    if task_type in VISION_TASKS:
        return (LLMProvider.OPENAI, LLMModel.GPT_4O_MINI.value)

    # Config registry override (production.yaml / models.yaml)
    try:
        from packages.core.config.model_registry import get_model_for_task_key

        model = get_model_for_task_key(task_type)
        if model:
            return (_detect_provider_from_model(model), model)
    except Exception:
        pass

    # Task-based routing — Groq (openai/gpt-oss-120b) is the primary text-generation
    # model for every task below; only vision tasks (handled above) stay on OpenAI.
    _GROQ_PRIMARY = (LLMProvider.GROQ, getattr(settings, "PRIMARY_LLM_MODEL", LLMModel.GPT_OSS_120B.value))
    task_routing = {
        # Studio structured tasks
        "quiz": _GROQ_PRIMARY,
        "flashcards": _GROQ_PRIMARY,
        "mind_map": _GROQ_PRIMARY,
        "slide_deck": _GROQ_PRIMARY,
        "intent_classifier": _GROQ_PRIMARY,
        "query_rewriter": _GROQ_PRIMARY,
        "scope_narrower": _GROQ_PRIMARY,
        # Ingestion-time chunk contextualization (Contextual Retrieval)
        "chunk_contextualization": _GROQ_PRIMARY,
        # Admin NCERT global corpus (overridable via settings.NCERT_GLOBAL_CONTEXT_MODEL at call site)
        "ncert_chunk_contextualization": _GROQ_PRIMARY,
        # Optional: query decomposition for retrieval (production-gated)
        "query_decomposer": _GROQ_PRIMARY,

        # Chat
        "chat": _GROQ_PRIMARY,
        "tutor_follow_ups": _GROQ_PRIMARY,
        "problem_solver_dna": _GROQ_PRIMARY,
        "problem_solver_mode": _GROQ_PRIMARY,
        "source_question_extract": _GROQ_PRIMARY,
    }

    return task_routing.get(task_type, _GROQ_PRIMARY)


