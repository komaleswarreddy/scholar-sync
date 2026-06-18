"""
Model and prompt version registry.

Production loads config/production.yaml; experiments use config/models.yaml.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

ROOT = Path(__file__).resolve().parents[3]
MODELS_YAML = ROOT / "config" / "models.yaml"
PRODUCTION_YAML = ROOT / "config" / "production.yaml"


def _use_production() -> bool:
    if os.environ.get("EVAL_USE_PRODUCTION_CONFIG", "").lower() in ("1", "true", "yes"):
        return True
    try:
        from config.settings import settings

        return getattr(settings, "ENVIRONMENT", "development") == "production"
    except Exception:
        return False


@lru_cache(maxsize=1)
def _load_models_doc() -> Dict[str, Any]:
    if not MODELS_YAML.is_file():
        return {"agents": {}, "default_model": "gpt-4o-mini"}
    with MODELS_YAML.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=1)
def _load_production_doc() -> Dict[str, Any]:
    if not PRODUCTION_YAML.is_file():
        return {"agents": {}}
    with PRODUCTION_YAML.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def reload_registry() -> None:
    _load_models_doc.cache_clear()
    _load_production_doc.cache_clear()


def list_agents() -> List[str]:
    if _use_production():
        return list((_load_production_doc().get("agents") or {}).keys())
    return list((_load_models_doc().get("agents") or {}).keys())


def get_agent_config(agent_name: str) -> Optional[Dict[str, Any]]:
    """Full config block for an agent."""
    if _use_production():
        agents = _load_production_doc().get("agents") or {}
        if agent_name in agents:
            return dict(agents[agent_name])
    models_doc = _load_models_doc()
    agents = models_doc.get("agents") or {}
    if agent_name in agents:
        cfg = dict(agents[agent_name])
        if "model" not in cfg:
            cfg["model"] = models_doc.get("default_model", "gpt-4o-mini")
        if "prompt" not in cfg:
            cfg["prompt"] = cfg.get("default_prompt", "v1")
        return cfg
    return None


def get_model(agent_name: str) -> Optional[str]:
    """Resolved model name for agent (production.yaml or models.yaml)."""
    cfg = get_agent_config(agent_name)
    if cfg and cfg.get("model"):
        return str(cfg["model"])
    return _load_models_doc().get("default_model", "gpt-4o-mini")


def get_prompt_version(agent_name: str) -> str:
    """Resolved prompt version slug (e.g. v1)."""
    cfg = get_agent_config(agent_name)
    if cfg:
        return str(cfg.get("prompt") or cfg.get("default_prompt") or "v1")
    return "v1"


def get_task_key(agent_name: str) -> Optional[str]:
    cfg = get_agent_config(agent_name)
    if cfg and cfg.get("task_key"):
        return str(cfg["task_key"])
    return agent_name


def get_candidate_models(agent_name: str) -> List[str]:
    models_doc = _load_models_doc()
    agents = models_doc.get("agents") or {}
    if agent_name in agents:
        return list(agents[agent_name].get("models") or [models_doc.get("default_model", "gpt-4o-mini")])
    return list(models_doc.get("candidate_models") or ["gpt-4o-mini"])


def get_prompt_versions(agent_name: str) -> List[str]:
    models_doc = _load_models_doc()
    agents = models_doc.get("agents") or {}
    if agent_name in agents:
        return list(agents[agent_name].get("prompt_versions") or ["v1"])
    return ["v1"]


def get_passing_threshold(agent_name: str) -> float:
    models_doc = _load_models_doc()
    agents = models_doc.get("agents") or {}
    if agent_name in agents:
        return float(agents[agent_name].get("passing_threshold", 90))
    return 90.0


def get_agent_by_task_key(task_key: str) -> Optional[str]:
    """Resolve agent name from LLM task_key (e.g. quiz -> studio_quiz)."""
    if _use_production():
        agents = _load_production_doc().get("agents") or {}
    else:
        agents = _load_models_doc().get("agents") or {}
    for name, cfg in agents.items():
        if str(cfg.get("task_key", "")) == task_key:
            return name
    if task_key in agents:
        return task_key
    return None


def get_model_for_task_key(task_key: str) -> Optional[str]:
    agent = get_agent_by_task_key(task_key) or task_key
    return get_model(agent)


def get_evaluator_name(agent_name: str) -> str:
    models_doc = _load_models_doc()
    agents = models_doc.get("agents") or {}
    if agent_name in agents:
        return str(agents[agent_name].get("evaluator", "formatter"))
    return "formatter"
