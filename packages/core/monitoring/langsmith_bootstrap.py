"""Configure LangSmith tracing from application settings."""

from __future__ import annotations

import os
from typing import Any, Dict

from config.settings import settings


def configure_langsmith_tracing() -> Dict[str, Any]:
    """
    Apply LangSmith env vars so LangGraph / LangChain auto-trace LLM calls.

    Must run before importing LangGraph pipelines when possible.
    """
    enabled = bool(settings.LANGSMITH_TRACING_ENABLED and (settings.LANGSMITH_API_KEY or "").strip())
    if not enabled:
        return {
            "enabled": False,
            "project": settings.LANGSMITH_PROJECT,
            "endpoint": settings.LANGSMITH_ENDPOINT,
        }

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY.strip()
    os.environ["LANGSMITH_PROJECT"] = (settings.LANGSMITH_PROJECT or "notebooklm-dev").strip()
    endpoint = (settings.LANGSMITH_ENDPOINT or "https://api.smith.langchain.com").strip()
    if endpoint:
        os.environ["LANGSMITH_ENDPOINT"] = endpoint

    return {
        "enabled": True,
        "project": os.environ["LANGSMITH_PROJECT"],
        "endpoint": endpoint,
    }
