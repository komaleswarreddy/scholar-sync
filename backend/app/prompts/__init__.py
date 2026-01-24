"""
Prompt Management System

Manages prompt templates, versioning, and loading.
Prompts are treated as first-class assets, not hardcoded strings.
"""

from .loader import PromptLoader, load_prompt
from .registry import PromptRegistry

__all__ = ['PromptLoader', 'load_prompt', 'PromptRegistry']
