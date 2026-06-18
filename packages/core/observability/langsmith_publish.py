"""
LangSmith publishing: datasets, experiment runs, evaluator feedback, cost metadata.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from packages.core.config.model_registry import get_evaluator_name, get_passing_threshold
from packages.core.monitoring.langsmith_bootstrap import configure_langsmith_tracing

ROOT = Path(__file__).resolve().parents[3]
PRICING_PATH = ROOT / "config" / "model_pricing.yaml"


def get_langsmith_project() -> str:
    return (
        os.environ.get("LANGSMITH_PROJECT")
        or os.environ.get("LANGCHAIN_PROJECT")
        or "notebooklm-dev"
    )


def ensure_tracing(project: Optional[str] = None) -> Dict[str, Any]:
    status = configure_langsmith_tracing()
    proj = project or get_langsmith_project()
    if status.get("enabled"):
        os.environ["LANGSMITH_PROJECT"] = proj
        status["project"] = proj
    return status


def get_client():
    from langsmith import Client

    return Client()


def load_pricing() -> Dict[str, Dict[str, float]]:
    if not PRICING_PATH.is_file():
        return {
            "gpt-4o-mini": {"input_per_1m_usd": 0.15, "output_per_1m_usd": 0.60},
            "gpt-4o": {"input_per_1m_usd": 2.50, "output_per_1m_usd": 10.00},
        }
    doc = yaml.safe_load(PRICING_PATH.read_text(encoding="utf-8")) or {}
    return doc.get("pricing") or {}


def estimate_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> Dict[str, float]:
    """Return input_cost, output_cost, total_cost in USD."""
    p = load_pricing().get(model, load_pricing().get("gpt-4o-mini", {}))
    in_rate = float(p.get("input_per_1m_usd", 0.15)) / 1_000_000
    out_rate = float(p.get("output_per_1m_usd", 0.60)) / 1_000_000
    input_cost = prompt_tokens * in_rate
    output_cost = completion_tokens * out_rate
    return {
        "prompt_tokens": float(prompt_tokens),
        "completion_tokens": float(completion_tokens),
        "total_tokens": float(prompt_tokens + completion_tokens),
        "input_cost_usd": round(input_cost, 6),
        "output_cost_usd": round(output_cost, 6),
        "total_cost_usd": round(input_cost + output_cost, 6),
    }


def publish_eval_example_run(
    *,
    agent_name: str,
    example_id: str,
    inputs: Dict[str, Any],
    output: Any,
    expected: Dict[str, Any],
    evaluator_name: str,
    score: float,
    passed: bool,
    metrics: Dict[str, float],
    model: str,
    prompt_version: str,
    dataset_name: str,
    dataset_hash: str,
    variation: str = "",
    tags: Optional[List[str]] = None,
    parent_run_id: Optional[str] = None,
    prompt_tokens: Optional[int] = None,
    completion_tokens: Optional[int] = None,
    eval_batch_id: Optional[str] = None,
) -> Optional[str]:
    """Post one evaluated example as a LangSmith run with feedback scores."""
    status = ensure_tracing()
    if not status.get("enabled"):
        return None

    prompt_tok = prompt_tokens if prompt_tokens is not None else max(50, len(str(inputs)) // 4)
    completion_tok = completion_tokens if completion_tokens is not None else max(30, len(str(output)) // 4)
    costs = estimate_cost(model, prompt_tok, completion_tok)
    batch_id = eval_batch_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    try:
        from langsmith.run_trees import RunTree

        meta = {
            "run_kind": "eval_example",
            "agent_name": agent_name,
            "ls_model_name": model,
            "model": model,
            "prompt_version": prompt_version,
            "evaluator": evaluator_name,
            "dataset_name": dataset_name,
            "dataset_hash": dataset_hash,
            "example_id": example_id,
            "variation": variation,
            "tags": tags or [],
            "passed": passed,
            "weighted_score": score,
            "eval_batch_id": batch_id,
            **costs,
            **{f"metric_{k}": v for k, v in metrics.items()},
        }

        run = RunTree(
            name=f"eval/{agent_name}/{example_id}",
            run_type="llm",
            inputs={"inputs": inputs, "expected": expected, "model": model, "prompt_version": prompt_version},
            parent_run_id=parent_run_id,
            extra={"metadata": meta},
            project_name=get_langsmith_project(),
        )
        run.end(
            outputs={
                "output": output,
                "score": score,
                "passed": passed,
                "metrics": metrics,
                "cost": costs,
            },
            metadata={
                "ls_model_name": model,
                "prompt_tokens": prompt_tok,
                "completion_tokens": completion_tok,
                "total_tokens": prompt_tok + completion_tok,
            },
        )
        run.post()
        run_id = str(run.id)

        client = get_client()
        client.create_feedback(run_id, key="weighted_score", score=score / 100.0, comment=f"passed={passed}")
        client.create_feedback(run_id, key="passed", score=1.0 if passed else 0.0)
        for mk, mv in metrics.items():
            client.create_feedback(run_id, key=f"metric_{mk}", score=float(mv))
        client.create_feedback(
            run_id,
            key="total_cost_usd",
            score=min(1.0, costs["total_cost_usd"]),
            comment=f"in=${costs['input_cost_usd']:.6f} out=${costs['output_cost_usd']:.6f}",
        )
        return run_id
    except Exception as exc:
        print(f"[LANGSMITH] publish_eval_example_run failed: {exc}")
        return None


def publish_experiment_summary(
    *,
    agent_name: str,
    prompt_version: str,
    model: str,
    report: Dict[str, Any],
    row: Dict[str, Any],
    dataset_name: str,
    eval_batch_id: Optional[str] = None,
) -> Optional[str]:
    """Post experiment summary run (leaderboard row) to LangSmith."""
    status = ensure_tracing()
    if not status.get("enabled"):
        return None

    try:
        from langsmith.run_trees import RunTree

        evaluator = get_evaluator_name(agent_name)
        threshold = get_passing_threshold(agent_name)
        total_tokens = int(row.get("tokens", 400))
        prompt_tok = int(row.get("prompt_tokens", total_tokens * 2 // 3))
        completion_tok = int(row.get("completion_tokens", total_tokens // 3))
        costs = estimate_cost(model, prompt_tok, completion_tok)
        batch_id = eval_batch_id or report.get("eval_batch_id") or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        meta = {
            "run_kind": "experiment_summary",
            "agent_name": agent_name,
            "ls_model_name": model,
            "model": model,
            "prompt_version": prompt_version,
            "evaluator": evaluator,
            "passing_threshold": threshold,
            "dataset_name": dataset_name,
            "dataset_hash": report.get("dataset_hash"),
            "pass_rate": row.get("pass_rate"),
            "avg_latency_ms": row.get("latency_ms"),
            "eval_batch_id": batch_id,
            **costs,
        }

        run = RunTree(
            name=f"experiment/{agent_name}/{prompt_version}/{model}",
            run_type="llm",
            inputs={
                "agent": agent_name,
                "prompt": prompt_version,
                "model": model,
                "dataset": dataset_name,
            },
            extra={"metadata": meta},
            project_name=get_langsmith_project(),
        )
        run.end(
            outputs={"leaderboard_row": row, "winner": report.get("winner")},
            metadata={
                "ls_model_name": model,
                "prompt_tokens": prompt_tok,
                "completion_tokens": completion_tok,
                "total_tokens": prompt_tok + completion_tok,
            },
        )
        run.post()
        run_id = str(run.id)

        client = get_client()
        client.create_feedback(run_id, key="weighted_score", score=row.get("score", 0) / 100.0)
        client.create_feedback(run_id, key="passed", score=1.0 if row.get("passed") else 0.0)
        client.create_feedback(
            run_id,
            key="pass_rate",
            score=float(row.get("pass_rate", 0)),
        )
        return run_id
    except Exception as exc:
        print(f"[LANGSMITH] publish_experiment_summary failed: {exc}")
        return None


def publish_e2e_workflow_run(report: Dict[str, Any]) -> Optional[str]:
    status = ensure_tracing()
    if not status.get("enabled"):
        return None
    try:
        from langsmith.run_trees import RunTree

        run = RunTree(
            name="e2e/workflow_evaluation",
            run_type="chain",
            inputs={"samples": report.get("samples"), "threshold": report.get("threshold")},
            extra={
                "metadata": {
                    "run_kind": "e2e_workflow",
                    "workflow_score": report.get("workflow_score"),
                    "passed": report.get("passed"),
                }
            },
            project_name=get_langsmith_project(),
        )
        run.end(outputs=report)
        run.post()
        client = get_client()
        client.create_feedback(
            str(run.id),
            key="workflow_score",
            score=float(report.get("workflow_score", 0)) / 100.0,
        )
        client.create_feedback(
            str(run.id),
            key="passed",
            score=1.0 if report.get("passed") else 0.0,
        )
        return str(run.id)
    except Exception as exc:
        print(f"[LANGSMITH] publish_e2e_workflow_run failed: {exc}")
        return None
