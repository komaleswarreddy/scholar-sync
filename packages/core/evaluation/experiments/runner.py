"""
Experiment runner: Dataset x Prompt Versions x Models.

Persists leaderboard to evals/reports and optionally logs to LangSmith.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from packages.core.config.model_registry import (
  get_evaluator_name,
  get_passing_threshold,
  get_prompt_versions,
  get_candidate_models,
)
from packages.core.evaluation.datasets.loader import dataset_version_hash, load_agent_dataset
from packages.core.evaluation.evaluators.registry import get_evaluator
from packages.core.observability.langsmith import configure_eval_tracing

ROOT = Path(__file__).resolve().parents[4]
REPORTS_DIR = ROOT / "evals" / "reports"


@dataclass
class ExperimentRow:
  agent_name: str
  prompt_version: str
  model: str
  score: float
  pass_rate: float
  cost_usd: float
  latency_ms: float
  tokens: int
  passed: bool
  dataset_hash: str = ""
  metrics: Dict[str, float] = field(default_factory=dict)
  prompt_tokens: int = 0
  completion_tokens: int = 0
  input_cost_usd: float = 0.0
  output_cost_usd: float = 0.0


def _mock_agent_output(agent_name: str, record_input: Dict[str, Any], expected: Dict[str, Any]) -> Any:
  """Offline scoring: use expected as proxy output when no live agent hook."""
  if agent_name == "intent_classifier":
    return expected
  if agent_name == "query_rewriter":
    return expected if "queries" in expected else {"queries": [record_input.get("query", "")], "confidence": 0.9, "reasoning": "mock"}
  return expected


def _get_agent_output(
  *,
  live: bool,
  agent_name: str,
  prompt_version: str,
  model: str,
  record_input: Dict[str, Any],
  expected: Dict[str, Any],
) -> tuple[Any, int, int]:
  if not live:
    output = _mock_agent_output(agent_name, record_input, expected)
    pt = max(50, len(str(record_input)) // 4)
    ct = max(30, len(str(output)) // 4)
    return output, pt, ct
  from packages.core.evaluation.experiments.live_agent import invoke_agent_for_eval

  return invoke_agent_for_eval(agent_name, prompt_version, model, record_input)


def run_experiment(
  agent_name: str,
  *,
  dataset: Optional[str] = None,
  prompts: Optional[Sequence[str]] = None,
  models: Optional[Sequence[str]] = None,
  limit: Optional[int] = None,
  project: Optional[str] = None,
  publish_to_langsmith: bool = True,
  live: bool = True,
  eval_batch_id: Optional[str] = None,
) -> Dict[str, Any]:
  from packages.core.observability.langsmith_publish import (
    ensure_tracing,
    estimate_cost,
    get_langsmith_project,
    publish_eval_example_run,
    publish_experiment_summary,
  )

  proj = project or get_langsmith_project()
  batch_id = eval_batch_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
  configure_eval_tracing(project=proj)
  ensure_tracing(proj)
  agent_id = dataset or agent_name
  records = load_agent_dataset(agent_id, limit=limit)
  prompt_list = list(prompts or get_prompt_versions(agent_name))
  model_list = list(models or get_candidate_models(agent_name))
  evaluator = get_evaluator(get_evaluator_name(agent_name))
  threshold = get_passing_threshold(agent_name)
  ds_hash = dataset_version_hash(agent_id)
  dataset_name = f"nbm-prompt-{agent_id}"
  evaluator_name = get_evaluator_name(agent_name)
  langsmith_run_ids: List[str] = []
  example_results: List[Dict[str, Any]] = []

  rows: List[ExperimentRow] = []
  for prompt_v in prompt_list:
    for model in model_list:
      t0 = time.perf_counter()
      scores: List[float] = []
      passes = 0
      agg_metrics: Dict[str, List[float]] = {}
      total_prompt_tok = 0
      total_completion_tok = 0
      for rec in records:
        output, pt, ct = _get_agent_output(
          live=live,
          agent_name=agent_name,
          prompt_version=prompt_v,
          model=model,
          record_input=rec.input,
          expected=rec.expected_output,
        )
        result = evaluator.evaluate(inputs=rec.input, output=output, expected=rec.expected_output, metadata=rec.metadata)
        scores.append(result.score)
        if result.passed:
          passes += 1
        for k, v in result.metrics.items():
          agg_metrics.setdefault(k, []).append(float(v))
        total_prompt_tok += pt
        total_completion_tok += ct
        example_results.append({
          "example_id": rec.id,
          "prompt": prompt_v,
          "model": model,
          "variation": rec.variation,
          "score": round(result.score, 2),
          "passed": result.passed,
          "inputs": rec.input,
          "expected": rec.expected_output,
          "actual": output,
        })
        if publish_to_langsmith:
          rid = publish_eval_example_run(
            agent_name=agent_name,
            example_id=rec.id,
            inputs=rec.input,
            output=output,
            expected=rec.expected_output,
            evaluator_name=evaluator_name,
            score=result.score,
            passed=result.passed,
            metrics=result.metrics,
            model=model,
            prompt_version=prompt_v,
            dataset_name=dataset_name,
            dataset_hash=ds_hash,
            variation=rec.variation,
            tags=rec.tags,
            prompt_tokens=pt,
            completion_tokens=ct,
            eval_batch_id=batch_id,
          )
          if rid:
            langsmith_run_ids.append(rid)
      elapsed = (time.perf_counter() - t0) * 1000.0
      avg_score = sum(scores) / max(len(scores), 1)
      pass_rate = passes / max(len(scores), 1)
      mean_metrics = {k: sum(v) / len(v) for k, v in agg_metrics.items()}
      costs = estimate_cost(model, total_prompt_tok, total_completion_tok)
      rows.append(
        ExperimentRow(
          agent_name=agent_name,
          prompt_version=prompt_v,
          model=model,
          score=avg_score,
          pass_rate=pass_rate,
          cost_usd=costs["total_cost_usd"],
          latency_ms=elapsed / max(len(records), 1),
          tokens=int(costs["total_tokens"]),
          passed=avg_score >= threshold,
          dataset_hash=ds_hash,
          metrics=mean_metrics,
          prompt_tokens=total_prompt_tok,
          completion_tokens=total_completion_tok,
          input_cost_usd=costs["input_cost_usd"],
          output_cost_usd=costs["output_cost_usd"],
        )
      )

  leaderboard = sorted(rows, key=lambda r: (-r.score, r.cost_usd))
  report = {
    "agent_name": agent_name,
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "dataset_id": agent_id,
    "dataset_hash": ds_hash,
    "threshold": threshold,
    "live": live,
    "eval_batch_id": batch_id,
    "rows": [
      {
        "prompt": r.prompt_version,
        "model": r.model,
        "score": round(r.score, 2),
        "pass_rate": round(r.pass_rate, 4),
        "cost_usd": round(r.cost_usd, 6),
        "input_cost_usd": round(r.input_cost_usd, 6),
        "output_cost_usd": round(r.output_cost_usd, 6),
        "prompt_tokens": r.prompt_tokens,
        "completion_tokens": r.completion_tokens,
        "latency_ms": round(r.latency_ms, 2),
        "passed": r.passed,
        "metrics": r.metrics,
      }
      for r in leaderboard
    ],
    "winner": select_winner(leaderboard, threshold=threshold),
    "langsmith_project": proj,
    "langsmith_example_runs": len(langsmith_run_ids),
    "evaluator": evaluator_name,
    "example_results": example_results[:20],
  }
  REPORTS_DIR.mkdir(parents=True, exist_ok=True)
  out_path = REPORTS_DIR / f"experiment_{agent_name}.json"
  out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

  if publish_to_langsmith:
    for row_dict in report["rows"]:
      publish_experiment_summary(
        agent_name=agent_name,
        prompt_version=row_dict["prompt"],
        model=row_dict["model"],
        report=report,
        row=row_dict,
        dataset_name=dataset_name,
        eval_batch_id=batch_id,
      )
  return report


def select_winner(rows: Sequence[ExperimentRow], *, threshold: float = 90.0) -> Dict[str, Any]:
  """Cheapest configuration above threshold; tie-break with composite score."""
  eligible = [r for r in rows if r.score >= threshold]
  if not eligible:
    best = max(rows, key=lambda r: r.score) if rows else None
    return {"selected": False, "reason": "no_config_above_threshold", "best_effort": _row_dict(best) if best else None}

  def composite(r: ExperimentRow) -> float:
    quality = r.score / 100.0
    reliability = r.pass_rate
    latency_score = max(0.0, 1.0 - r.latency_ms / 10000.0)
    cost_eff = max(0.0, 1.0 - r.cost_usd / 1.0)
    return quality * 0.60 + reliability * 0.20 + latency_score * 0.10 + cost_eff * 0.10

  winner = max(eligible, key=composite)
  return {"selected": True, "winner": _row_dict(winner), "composite_score": round(composite(winner), 4)}


def _row_dict(r: Optional[ExperimentRow]) -> Optional[Dict[str, Any]]:
  if not r:
    return None
  return {
    "prompt": r.prompt_version,
    "model": r.model,
    "score": r.score,
    "cost_usd": r.cost_usd,
    "input_cost_usd": r.input_cost_usd,
    "output_cost_usd": r.output_cost_usd,
  }


def run_two_phase_experiment(
  agent_name: str,
  *,
  models: Optional[Sequence[str]] = None,
  limit: Optional[int] = None,
  live: bool = True,
) -> Dict[str, Any]:
  """Phase 1: fixed model x all prompts. Phase 2: top prompts x all models."""
  model_list = list(models or get_candidate_models(agent_name))
  base_model = model_list[0]
  prompts = get_prompt_versions(agent_name)

  phase1 = run_experiment(agent_name, prompts=prompts, models=[base_model], limit=limit, live=live)
  top_prompts = [r["prompt"] for r in phase1["rows"][:2]]
  phase2 = run_experiment(agent_name, prompts=top_prompts, models=model_list, limit=limit, live=live)
  winner = phase2.get("winner") or phase1.get("winner")
  return {"phase1": phase1, "phase2": phase2, "winner": winner}
