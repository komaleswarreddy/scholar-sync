"""Model matrix and LangSmith settings for intent classifier evals."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

DATASET_NAME = "nbm-prompt-intent_classifier"
AGENT_ID = "intent_classifier"
PROMPT_VERSIONS = ("v1", "v2", "v3")
JUDGE_MODEL = "gpt-4o"


@dataclass(frozen=True)
class ModelSpec:
    provider: str
    model: str
    label: str


MODEL_MATRIX: List[ModelSpec] = [
    ModelSpec(provider="openai", model="gpt-5.4-mini", label="openai-gpt-5.4-mini"),
    ModelSpec(provider="anthropic", model="claude-haiku-4-5", label="anthropic-claude-haiku-4-5"),
    ModelSpec(provider="openai", model="gpt-5-mini", label="openai-gpt-5-mini"),
]


def get_langsmith_project() -> str:
    return (
        os.environ.get("LANGSMITH_PROJECT")
        or os.environ.get("LANGCHAIN_PROJECT")
        or "ScholarSync"
    )


def ensure_langsmith_env() -> None:
    project = get_langsmith_project()
    os.environ["LANGSMITH_PROJECT"] = project
    os.environ["LANGCHAIN_PROJECT"] = project
    if (os.environ.get("LANGSMITH_API_KEY") or "").strip():
        os.environ["LANGSMITH_TRACING_ENABLED"] = "true"
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
