"""Load and render per-agent prompt versions (v1/v2/v3 from xlsx A/B/C)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Tuple

from jinja2 import Environment, FileSystemLoader, Undefined

from evals.agent_eval.config import PROMPT_VERSIONS

PROMPT_VERSIONS_ROOT = Path(__file__).resolve().parent / "prompt_versions"
# Production templates dir, so {% include 'problem_solver/...' %} resolves the
# same partials production uses (e.g. math_formatting_contract.j2).
_PROD_TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "packages" / "core" / "prompts" / "templates"


class _SilentUndefined(Undefined):
    """Render missing variables as empty instead of raising.

    Several agent prompts are the full production .j2 templates, which reference
    variables only present on some dataset rows (e.g. inferred_subject_hint) or
    iterate optional lists. A missing variable must never abort an eval run.
    """

    def __getattr__(self, _name: str) -> "Any":
        return self

    def __getitem__(self, _key: Any) -> "Any":
        return self

    def __call__(self, *_a: Any, **_k: Any) -> "Any":
        return self

    def __iter__(self):
        return iter(())

    def __str__(self) -> str:
        return ""

    def __bool__(self) -> bool:
        return False

    def __len__(self) -> int:
        return 0


# Mirror packages/core/prompts/loader.py so production .j2 templates render the
# same way here (block trimming, no HTML autoescape).
_JINJA_ENV = Environment(
    loader=FileSystemLoader(str(_PROD_TEMPLATES_DIR)) if _PROD_TEMPLATES_DIR.is_dir() else None,
    undefined=_SilentUndefined,
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
)


def _render(template_text: str, ctx: Dict[str, Any]) -> str:
    try:
        return _JINJA_ENV.from_string(template_text).render(**ctx)
    except Exception:
        return template_text


def _load_version_files(agent_id: str, version: str) -> Tuple[str, str]:
    agent_dir = PROMPT_VERSIONS_ROOT / agent_id
    system_path = agent_dir / f"{version}_system.txt"
    user_path = agent_dir / f"{version}_user.j2"
    if not system_path.is_file():
        raise FileNotFoundError(f"Missing system prompt for {agent_id}/{version}: {system_path}")
    if not user_path.is_file():
        raise FileNotFoundError(f"Missing user template for {agent_id}/{version}: {user_path}")
    return system_path.read_text(encoding="utf-8"), user_path.read_text(encoding="utf-8")


@lru_cache(maxsize=128)
def get_prompt_parts(agent_id: str, version: str) -> Tuple[str, str]:
    if version not in PROMPT_VERSIONS:
        raise ValueError(f"Unknown prompt version {version!r}; expected one of {PROMPT_VERSIONS}")
    return _load_version_files(agent_id, version)


def render_prompts(agent_id: str, version: str, inputs: Dict[str, Any]) -> Tuple[str, str]:
    """Render (system, user) for a dataset example input dict.

    Both templates are Jinja-rendered. Many agent system prompts are the full
    production .j2 (with {{ vars }} / {% if %} / {% for %}); rendering the system
    here injects the dataset inputs exactly as production does.
    """
    system, user_template = get_prompt_parts(agent_id, version)
    render_ctx: Dict[str, Any] = dict(inputs or {})
    render_ctx.setdefault("context_block", "")
    system_rendered = _render(system, render_ctx)
    user = _render(user_template, render_ctx)
    return system_rendered, user


def list_versions() -> tuple[str, ...]:
    return PROMPT_VERSIONS
