#!/usr/bin/env python3
"""
Export a COMPLETE intent_classifier eval report to CSV.

Pulls every root run from the 6 LangSmith experiment sessions
(v1/v2/v3 x openai/anthropic), joins:
  - dataset gold (intent/scope/flags/confidence/reasoning) + variation + tags
  - model prediction (parsed 6-field output)
  - every per-example evaluator score + comment
  - llm-as-judge (gpt-4o) score + comment
  - tokens (prompt/completion/total), cost (LangSmith + computed from pricing)
  - latency + time-to-first-token
  - the exact system prompt + rendered user prompt per row
  - input schema + output schema

Outputs:
  evals/reports/intent_classifier_langsmith/full_report_detailed_<ts>.csv  (378 rows)
  evals/reports/intent_classifier_langsmith/full_report_summary_<ts>.csv   (6 rows + winner)

Usage:
  python scripts/export_intent_classifier_full_report.py
  python scripts/export_intent_classifier_full_report.py --report <stepwise_matrix.json>
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import yaml  # noqa: E402

from evals.intent_classifier_eval.config import (  # noqa: E402
    DATASET_NAME,
    ensure_langsmith_env,
)
from evals.intent_classifier_eval.prompts import get_prompt_parts, render_prompts  # noqa: E402

REPORTS_DIR = ROOT / "evals" / "reports" / "intent_classifier_langsmith"
PRICING_PATH = ROOT / "config" / "model_pricing.yaml"

DETERMINISTIC_KEYS = [
    "schema_validity",
    "intent_match",
    "routing_metadata_match",
    "routing_consistency",
    "confidence_calibration",
]
JUDGE_KEY = "llm_routing_judge"
GOLD_FIELDS = ["intent", "scope", "requires_retrieval", "requires_attachment", "confidence", "reasoning"]


def _load_pricing() -> Dict[str, Dict[str, float]]:
    doc = yaml.safe_load(PRICING_PATH.read_text(encoding="utf-8")) or {}
    return doc.get("pricing") or {}


def _latest_report() -> Optional[Path]:
    candidates = sorted(REPORTS_DIR.glob("stepwise_matrix_*.json"))
    return candidates[-1] if candidates else None


def _load_experiments_from_checkpoint() -> List[Dict[str, Any]]:
    """All completed experiments from step_checkpoint.json (source of truth)."""
    ckpt_path = REPORTS_DIR / "step_checkpoint.json"
    if not ckpt_path.is_file():
        return []
    ckpt = json.loads(ckpt_path.read_text(encoding="utf-8"))
    rows = list((ckpt.get("completed") or {}).values())
    # Stable sort: prompt version then model
    rows.sort(key=lambda r: (r.get("prompt_version", ""), r.get("model", "")))
    return rows


def _load_experiments(report_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    from_ckpt = _load_experiments_from_checkpoint()
    if from_ckpt:
        return from_ckpt
    if report_path is None:
        report_path = _latest_report()
    if not report_path:
        return []
    doc = json.loads(report_path.read_text(encoding="utf-8"))
    return doc.get("experiments") or []


def _example_map(client) -> Dict[str, Dict[str, Any]]:
    """example_id -> {inputs, outputs(gold), variation, tags}."""
    ds = client.read_dataset(dataset_name=DATASET_NAME)
    out: Dict[str, Dict[str, Any]] = {}
    for ex in client.list_examples(dataset_id=ds.id):
        meta = getattr(ex, "metadata", None) or {}
        out[str(ex.id)] = {
            "inputs": getattr(ex, "inputs", {}) or {},
            "gold": getattr(ex, "outputs", {}) or {},
            "variation": meta.get("variation", "unknown"),
            "tags": meta.get("tags", []),
            "dataset_item_id": meta.get("id"),
        }
    return out


def _feedback_for_runs(client, run_ids: List[str]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """run_id -> {feedback_key -> {score, comment}}."""
    fb: Dict[str, Dict[str, Dict[str, Any]]] = {}
    if not run_ids:
        return fb
    try:
        for f in client.list_feedback(run_ids=run_ids):
            rid = str(getattr(f, "run_id", "") or "")
            key = getattr(f, "key", None)
            if not rid or not key:
                continue
            fb.setdefault(rid, {})[key] = {
                "score": getattr(f, "score", None),
                "comment": getattr(f, "comment", None),
            }
    except Exception as exc:
        print(f"WARN: list_feedback failed: {exc}")
    return fb


def _seconds(start, end) -> Optional[float]:
    try:
        if start and end:
            return round((end - start).total_seconds(), 3)
    except Exception:
        pass
    return None


def _parse_ts(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        s = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _ttft_seconds(run) -> Optional[float]:
    start = getattr(run, "start_time", None)
    if not start:
        return None
    ftt = getattr(run, "first_token_time", None)
    if ftt:
        try:
            return round((ftt - start).total_seconds(), 3)
        except Exception:
            pass
    # Fall back to the mirrored "new_token" event timestamp on the root run.
    events = getattr(run, "events", None) or []
    for e in events:
        if not isinstance(e, dict) or e.get("name") != "new_token":
            continue
        ts = _parse_ts(e.get("time"))
        if ts is None:
            continue
        try:
            start_aware = start if start.tzinfo else start.replace(tzinfo=timezone.utc)
            ts_aware = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
            return round((ts_aware - start_aware).total_seconds(), 3)
        except Exception:
            return None
    return None


def _num(value) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def collect(experiments: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    ensure_langsmith_env()
    from langsmith import Client

    client = Client()
    pricing = _load_pricing()
    examples = _example_map(client)

    if experiments is None:
        experiments = _load_experiments()
    if not experiments:
        raise SystemExit("No experiments in checkpoint or stepwise_matrix report")
    print(f"Exporting {len(experiments)} experiment(s) from checkpoint/report")

    detailed_rows: List[Dict[str, Any]] = []
    summary_rows: List[Dict[str, Any]] = []

    for exp in experiments:
        exp_name = exp.get("experiment_name")
        version = exp.get("prompt_version")
        provider = exp.get("provider")
        model = exp.get("model")
        if not exp_name:
            continue

        try:
            system_prompt, _user_tmpl = get_prompt_parts(version)
        except Exception:
            system_prompt = ""

        rates = pricing.get(model) or {}
        in_rate = float(rates.get("input_per_1m_usd", 0.0)) / 1_000_000
        out_rate = float(rates.get("output_per_1m_usd", 0.0)) / 1_000_000

        print(f"  reading runs for {exp_name} ...")
        roots = list(client.list_runs(project_name=exp_name, is_root=True))
        run_ids = [str(r.id) for r in roots]
        feedback = _feedback_for_runs(client, run_ids)

        agg = {k: [] for k in DETERMINISTIC_KEYS}
        agg_judge: List[float] = []
        tot_pt = tot_ct = 0
        tot_cost = 0.0
        latencies: List[float] = []
        ttfts: List[float] = []

        for run in roots:
            rid = str(run.id)
            ref_id = str(getattr(run, "reference_example_id", "") or "")
            ex = examples.get(ref_id, {})
            gold = ex.get("gold", {}) or {}
            inputs = ex.get("inputs", {}) or {}
            pred = getattr(run, "outputs", {}) or {}
            if not isinstance(pred, dict):
                pred = {}

            try:
                _sys, user_rendered = render_prompts(version, inputs)
            except Exception:
                user_rendered = ""

            pt = int(getattr(run, "prompt_tokens", 0) or 0)
            ct = int(getattr(run, "completion_tokens", 0) or 0)
            tt = int(getattr(run, "total_tokens", 0) or 0) or (pt + ct)
            ls_cost = getattr(run, "total_cost", None)
            computed_cost = round(pt * in_rate + ct * out_rate, 8)
            latency = _seconds(getattr(run, "start_time", None), getattr(run, "end_time", None))
            ttft = _ttft_seconds(run)

            tot_pt += pt
            tot_ct += ct
            tot_cost += computed_cost
            if latency is not None:
                latencies.append(latency)
            if ttft is not None:
                ttfts.append(ttft)

            run_fb = feedback.get(rid, {})

            row: Dict[str, Any] = {
                "agent_id": "intent_classifier",
                "dataset_name": DATASET_NAME,
                "experiment_name": exp_name,
                "prompt_version": version,
                "provider": provider,
                "model": model,
                "model_label": model,
                "input_schema": ",".join(["query", "source_count"]),
                "output_schema": ",".join(GOLD_FIELDS),
                "example_id": ex.get("dataset_item_id") or ref_id,
                "reference_example_id": ref_id,
                "run_id": rid,
                "variation": ex.get("variation"),
                "tags": "|".join(ex.get("tags") or []),
                "input_query": inputs.get("query"),
                "input_source_count": inputs.get("source_count"),
                "input_json": json.dumps(inputs, ensure_ascii=False),
                "system_prompt": system_prompt,
                "user_prompt_rendered": user_rendered,
            }
            for f in GOLD_FIELDS:
                row[f"gold_{f}"] = gold.get(f)
            row["gold_json"] = json.dumps(gold, ensure_ascii=False)
            for f in GOLD_FIELDS:
                row[f"pred_{f}"] = pred.get(f)
            row["pred_json"] = json.dumps(pred, ensure_ascii=False)

            example_scores = []
            for k in DETERMINISTIC_KEYS:
                sc = run_fb.get(k, {}).get("score")
                row[f"score_{k}"] = sc
                row[f"comment_{k}"] = run_fb.get(k, {}).get("comment")
                if sc is not None:
                    agg[k].append(_num(sc))
                    example_scores.append(_num(sc))
            row["score_llm_routing_judge"] = run_fb.get(JUDGE_KEY, {}).get("score")
            row["comment_llm_routing_judge"] = run_fb.get(JUDGE_KEY, {}).get("comment")
            if run_fb.get(JUDGE_KEY, {}).get("score") is not None:
                agg_judge.append(_num(run_fb[JUDGE_KEY]["score"]))

            row["example_mean_deterministic_score"] = (
                round(sum(example_scores) / len(example_scores), 4) if example_scores else None
            )
            row["intent_correct"] = (
                1 if (pred.get("intent") and pred.get("intent") == gold.get("intent")) else 0
            )

            row["prompt_tokens"] = pt
            row["completion_tokens"] = ct
            row["total_tokens"] = tt
            row["langsmith_total_cost_usd"] = ls_cost
            row["computed_input_cost_usd"] = round(pt * in_rate, 8)
            row["computed_output_cost_usd"] = round(ct * out_rate, 8)
            row["computed_total_cost_usd"] = computed_cost
            row["latency_seconds"] = latency
            row["ttft_seconds"] = ttft
            row["run_status"] = getattr(run, "status", None)
            row["error"] = getattr(run, "error", None)
            row["start_time"] = str(getattr(run, "start_time", "") or "")
            row["end_time"] = str(getattr(run, "end_time", "") or "")

            detailed_rows.append(row)

        n = len(roots)
        means = {k: (round(sum(v) / len(v), 4) if v else None) for k, v in agg.items()}
        mean_judge = round(sum(agg_judge) / len(agg_judge), 4) if agg_judge else None
        all_det = [s for v in agg.values() for s in v]
        overall = round(sum(all_det) / len(all_det), 4) if all_det else 0.0

        summary_rows.append(
            {
                "experiment_name": exp_name,
                "prompt_version": version,
                "provider": provider,
                "model": model,
                "model_label": model,
                "n_examples": n,
                "intent_accuracy": means.get("intent_match"),
                "mean_schema_validity": means.get("schema_validity"),
                "mean_intent_match": means.get("intent_match"),
                "mean_routing_metadata_match": means.get("routing_metadata_match"),
                "mean_routing_consistency": means.get("routing_consistency"),
                "mean_confidence_calibration": means.get("confidence_calibration"),
                "mean_llm_routing_judge": mean_judge,
                "overall_mean_deterministic_score": overall,
                "total_prompt_tokens": tot_pt,
                "total_completion_tokens": tot_ct,
                "total_tokens": tot_pt + tot_ct,
                "total_cost_usd": round(tot_cost, 6),
                "avg_cost_per_example_usd": round(tot_cost / n, 8) if n else None,
                "avg_latency_seconds": round(sum(latencies) / len(latencies), 3) if latencies else None,
                "avg_ttft_seconds": round(sum(ttfts) / len(ttfts), 3) if ttfts else None,
                "elapsed_seconds": exp.get("elapsed_seconds"),
                "system_prompt": system_prompt,
                "is_winner": False,
            }
        )

    # Winner: rank by intent accuracy, then overall mean, then judge, then lower cost.
    if summary_rows:
        def _key(r):
            return (
                r.get("intent_accuracy") or 0,
                r.get("overall_mean_deterministic_score") or 0,
                r.get("mean_llm_routing_judge") or 0,
                -(r.get("total_cost_usd") or 0),
            )

        winner = max(summary_rows, key=_key)
        winner["is_winner"] = True
        for r in detailed_rows:
            r["is_winner_experiment"] = (r["experiment_name"] == winner["experiment_name"])

    return {"detailed": detailed_rows, "summary": summary_rows}


def _write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        print(f"WARN: no rows for {path.name}")
        return
    fieldnames: List[str] = []
    for r in rows:
        for k in r.keys():
            if k not in fieldnames:
                fieldnames.append(k)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    print(f"Wrote {len(rows)} rows -> {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default=None, help="Path to stepwise_matrix_*.json (default: latest)")
    args = parser.parse_args()

    report_path = Path(args.report) if args.report else None
    if report_path:
        experiments = _load_experiments(report_path)
    else:
        experiments = _load_experiments()
    data = collect(experiments)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    detailed_path = REPORTS_DIR / f"full_report_detailed_{ts}.csv"
    summary_path = REPORTS_DIR / f"full_report_summary_{ts}.csv"
    _write_csv(detailed_path, data["detailed"])
    _write_csv(summary_path, data["summary"])

    winner = next((r for r in data["summary"] if r.get("is_winner")), None)
    if winner:
        print(
            f"\nWINNER: {winner['prompt_version']} / {winner['model']} "
            f"| intent_acc={winner['intent_accuracy']} "
            f"| overall={winner['overall_mean_deterministic_score']} "
            f"| judge={winner['mean_llm_routing_judge']} "
            f"| cost=${winner['total_cost_usd']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
