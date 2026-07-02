"""Load and render intent classifier prompt versions (6-field contract)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Tuple

from jinja2 import Template

from evals.intent_classifier_eval.config import PROMPT_VERSIONS

VERSIONS_DIR = Path(__file__).resolve().parent / "prompt_versions"


def _load_version_files(version: str) -> Tuple[str, str]:
    system_path = VERSIONS_DIR / f"{version}_system.txt"
    user_path = VERSIONS_DIR / f"{version}_user.j2"
    if not system_path.is_file() or not user_path.is_file():
        raise FileNotFoundError(f"Missing prompt files for {version}")
    return system_path.read_text(encoding="utf-8"), user_path.read_text(encoding="utf-8")


def get_prompt_parts(version: str) -> Tuple[str, str]:
    """Return (system_prompt, user_template_jinja) for a version slug."""
    if version not in PROMPT_VERSIONS:
        raise ValueError(f"Unknown prompt version {version!r}; expected one of {PROMPT_VERSIONS}")
    return _load_version_files(version)


def render_prompts(version: str, inputs: Dict[str, Any]) -> Tuple[str, str]:
    """Render (system, user) for a dataset example input dict."""
    system, user_template = get_prompt_parts(version)
    render_ctx: Dict[str, Any] = {"context_block": "", "source_count": None}
    render_ctx.update(inputs or {})
    user = Template(user_template).render(**render_ctx)
    return system, user


def list_versions() -> tuple[str, ...]:
    return PROMPT_VERSIONS
