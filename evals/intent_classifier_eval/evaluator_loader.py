"""Load deterministic evaluators from evals/datasets/final_Evalutors (not a Python package)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, List

_EVAL_MODULE: ModuleType | None = None
_EVAL_PATH = (
    Path(__file__).resolve().parents[1]
    / "datasets"
    / "final_Evalutors"
    / "intent_classifier.py"
)

_LANGSMITH_ALLOWED = frozenset({"key", "score", "comment"})


def _langsmith_wrap(fn: Callable) -> Callable:
    """Strip extra fields so LangSmith EvaluationResult accepts the payload."""

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
    """Summary evaluators: keep score/key/comment; fold rich payload into comment."""

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


def load_intent_classifier_evaluators() -> ModuleType:
    global _EVAL_MODULE
    if _EVAL_MODULE is not None:
        return _EVAL_MODULE
    spec = importlib.util.spec_from_file_location("intent_classifier_evaluators", _EVAL_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load evaluators from {_EVAL_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["intent_classifier_evaluators"] = mod
    spec.loader.exec_module(mod)
    _EVAL_MODULE = mod
    return mod


def get_per_example_evaluators() -> List[Any]:
    mod = load_intent_classifier_evaluators()
    return [_langsmith_wrap(fn) for fn in mod.PER_EXAMPLE_EVALUATORS]


def get_summary_evaluators() -> List[Any]:
    mod = load_intent_classifier_evaluators()
    return [_langsmith_wrap_summary(fn) for fn in mod.SUMMARY_EVALUATORS]


def parse_model_response(
    raw_text: str,
    *,
    refusal: str | None = None,
    finish_reason: str | None = None,
) -> dict:
    mod = load_intent_classifier_evaluators()
    return mod.parse_model_response_to_outputs(
        raw_text,
        refusal=refusal,
        finish_reason=finish_reason,
    )


def compute_severity_summary(runs: list, examples: list) -> dict:
    """Run raw summary evaluator (with full fields) for local reporting."""
    mod = load_intent_classifier_evaluators()
    return mod.severity_tier_summary(runs, examples)
