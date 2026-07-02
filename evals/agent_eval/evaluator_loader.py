"""Dynamically load evaluators from evals/datasets/final_Evalutors."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, List, Optional

from evals.agent_eval.registry import AGENTS_REQUIRING_JUDGE, get_agent_spec

_LANGSMITH_ALLOWED = frozenset({"key", "score", "comment"})
_MODULE_CACHE: dict[str, ModuleType] = {}


def _langsmith_wrap(fn: Callable) -> Callable:
    def wrapped(run: Any, example: Any) -> dict:
        result = fn(run, example)
        if not isinstance(result, dict):
            return {"key": getattr(fn, "__name__", "evaluator"), "score": 0.0, "comment": "invalid result"}
        out = {k: result[k] for k in _LANGSMITH_ALLOWED if k in result}
        extras = {k: v for k, v in result.items() if k not in _LANGSMITH_ALLOWED}
        if extras:
            extra_note = json.dumps(extras, default=str)[:1500]
            out["comment"] = f"{out.get('comment', '')} | extras={extra_note}".strip(" |")
        if "key" not in out:
            out["key"] = getattr(fn, "__name__", "evaluator")
        return out

    wrapped.__name__ = getattr(fn, "__name__", "wrapped_evaluator")
    return wrapped


def _langsmith_wrap_summary(fn: Callable) -> Callable:
    def wrapped(runs: list, examples: list) -> dict:
        result = fn(runs, examples)
        if not isinstance(result, dict):
            return {"key": "summary", "score": 0.0, "comment": "invalid summary"}
        comment_parts = [str(result.get("comment", ""))]
        for field in (
            "ship_recommendation",
            "tier_0_blocking_count",
            "tier_1_serious_rate",
            "per_variation_intent_pass_rate",
            "per_field_pass_rate",
        ):
            if field in result:
                comment_parts.append(f"{field}={json.dumps(result[field], default=str)[:800]}")
        return {
            "key": result.get("key", getattr(fn, "__name__", "summary")),
            "score": result.get("score", 0.0),
            "comment": " | ".join(p for p in comment_parts if p),
        }

    wrapped.__name__ = getattr(fn, "__name__", "wrapped_summary")
    return wrapped


def load_evaluator_module(agent_id: str) -> ModuleType:
    if agent_id in _MODULE_CACHE:
        return _MODULE_CACHE[agent_id]
    spec_info = get_agent_spec(agent_id)
    path = spec_info.evaluator_path
    mod_name = f"agent_evaluators_{agent_id}"
    spec = importlib.util.spec_from_file_location(mod_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load evaluators from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    _MODULE_CACHE[agent_id] = mod
    return mod


def get_per_example_evaluators(agent_id: str, judge_llm: Optional[Callable[[str], str]] = None) -> List[Any]:
    mod = load_evaluator_module(agent_id)
    if agent_id in AGENTS_REQUIRING_JUDGE:
        if not hasattr(mod, "build_per_example_evaluators"):
            raise RuntimeError(f"{agent_id} requires build_per_example_evaluators(judge_llm)")
        if judge_llm is None:
            from evals.agent_eval.llm_judge import make_judge_llm

            judge_llm = make_judge_llm(agent_id)
        return [_langsmith_wrap(fn) for fn in mod.build_per_example_evaluators(judge_llm)]
    evaluators = getattr(mod, "PER_EXAMPLE_EVALUATORS", None)
    if evaluators is None:
        raise RuntimeError(f"No PER_EXAMPLE_EVALUATORS in {agent_id}")
    return [_langsmith_wrap(fn) for fn in evaluators]


def get_summary_evaluators(agent_id: str) -> List[Any]:
    mod = load_evaluator_module(agent_id)
    return [_langsmith_wrap_summary(fn) for fn in mod.SUMMARY_EVALUATORS]


def parse_model_response(agent_id: str, raw_text: str, **kwargs: Any) -> dict:
    mod = load_evaluator_module(agent_id)
    fn = mod.parse_model_response_to_outputs
    try:
        return fn(raw_text, **kwargs)
    except TypeError:
        return fn(raw_text)
