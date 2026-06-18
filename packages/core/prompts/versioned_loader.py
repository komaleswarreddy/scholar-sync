"""
Versioned prompt loader.

API:
    load_versioned_prompt(agent_name, version=None, part="template", **kwargs)
    get_template_paths(agent_name, version=None) -> dict
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from packages.core.config.model_registry import get_prompt_version
from packages.core.prompts.loader import load_prompt

ROOT = Path(__file__).resolve().parents[3]
PROMPTS_ROOT = ROOT / "prompts"
REGISTRY_YAML = PROMPTS_ROOT / "registry.yaml"


@lru_cache(maxsize=1)
def _load_registry() -> Dict[str, Any]:
    if not REGISTRY_YAML.is_file():
        return {"agents": {}}
    with REGISTRY_YAML.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def reload_prompt_registry() -> None:
    _load_registry.cache_clear()


def _resolve_version(agent_name: str, version: Optional[str]) -> str:
    if version:
        return version
    return get_prompt_version(agent_name)


def get_template_paths(agent_name: str, version: Optional[str] = None) -> Dict[str, str]:
    """Return template path map for agent version (system/user/template keys)."""
    ver = _resolve_version(agent_name, version)
    agents = _load_registry().get("agents") or {}
    agent_block = agents.get(agent_name) or {}
    ver_block = agent_block.get(ver)
    if not ver_block:
        default_ver = agent_block.get("default", "v1")
        ver_block = agent_block.get(default_ver) or {}
    return dict(ver_block)


def _override_text(agent_name: str, version: str) -> Optional[str]:
    """Optional plain-text override at prompts/{agent}/{version}.txt"""
    path = PROMPTS_ROOT / agent_name / f"{version}.txt"
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return None


def load_versioned_prompt(
    agent_name: str,
    version: Optional[str] = None,
    part: str = "template",
    **kwargs: Any,
) -> str:
    """
    Load and render a versioned prompt for an agent.

    Args:
        agent_name: Registry agent id (e.g. intent_classifier)
        version: Prompt version slug; defaults to production/models config
        part: Which template part — template, system, or user
        **kwargs: Jinja variables passed to template render
    """
    ver = _resolve_version(agent_name, version)
    override = _override_text(agent_name, ver)
    if override and part == "template":
        # Simple {{var}} substitution for override files without full Jinja
        out = override
        for k, v in kwargs.items():
            out = out.replace("{{ " + k + " }}", str(v)).replace("{{" + k + "}}", str(v))
        return out

    paths = get_template_paths(agent_name, ver)
    template_path = paths.get(part) or paths.get("template")
    if not template_path:
        raise FileNotFoundError(f"No prompt template for agent={agent_name} version={ver} part={part}")
    return load_prompt(template_path, **kwargs)


def load_agent_system_user(
    agent_name: str,
    version: Optional[str] = None,
    user_kwargs: Optional[Dict[str, Any]] = None,
    system_kwargs: Optional[Dict[str, Any]] = None,
) -> tuple[str, str]:
    """Load (system_prompt, user_prompt) for dual-template agents."""
    sk = system_kwargs or {}
    uk = user_kwargs or {}
    system = load_versioned_prompt(agent_name, version, part="system", **sk)
    user = load_versioned_prompt(agent_name, version, part="user", **uk)
    return system, user
