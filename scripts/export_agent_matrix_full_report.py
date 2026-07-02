#!/usr/bin/env python3
"""
Export COMPLETE per-example ("pin-to-pin") eval reports for the 14-agent matrix,
matching the intent_classifier full-report format.

Experiments are spread across MULTIPLE LangSmith workspaces (one per API key /
org, each with its own 5k trace quota). LangSmith data is workspace-isolated, so
this script groups every completed experiment by tenant and reads it back with
the API key for that workspace. Reads do NOT consume trace quota.

For each completed experiment (from step_checkpoint.json) it joins:
  - dataset gold outputs + variation + tags + raw input
  - the model prediction (full output JSON, flattened by output_keys)
  - every per-example evaluator score + comment (collected dynamically)
  - tokens (prompt/completion/total), cost (LangSmith + computed from pricing)
  - latency + time-to-first-token (when available)
  - the exact system prompt + rendered user prompt per row
  - input schema + output schema

Special rule: chat_policy_block and hallucination_guard_retry only export v1
(v2/v3 system prompts are identical copies of v1 -> skipped).

Outputs (evals/reports/agent_matrix_full/):
  full_report_detailed_<ts>.csv      one row per (experiment x example)
  full_report_summary_<ts>.csv       one row per experiment (+ per-agent winner)
  per_agent/<agent_id>_detailed_<ts>.csv

Usage:
  python scripts/export_agent_matrix_full_report.py
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

import yaml  # noqa: E402

from evals.agent_eval.config import dataset_name  # noqa: E402
from evals.agent_eval.prompts import get_prompt_parts, render_prompts  # noqa: E402
from evals.agent_eval.registry import get_agent_spec  # noqa: E402

import os  # noqa: E402

import requests  # noqa: E402

CKPT_PATH = ROOT / "evals" / "reports" / "agent_matrix" / "step_checkpoint.json"
REPORTS_DIR = ROOT / "evals" / "reports" / "agent_matrix_full"
PRICING_PATH = ROOT / "config" / "model_pricing.yaml"
KEYS_STORE = ROOT / "evals" / "reports" / "agent_matrix" / "workspace_keys.json"
KEYS_CACHE = ROOT / "evals" / "reports" / "agent_matrix" / "workspace_keys_cache.json"
LANGSMITH_ENDPOINT = "https://api.smith.langchain.com"


def _resolve_tenant(api_key: str) -> Optional[str]:
    """Resolve the workspace/tenant id for an API key (cached)."""
    try:
        r = requests.get(
            f"{LANGSMITH_ENDPOINT}/api/v1/workspaces",
            headers={"x-api-key": api_key},
            timeout=20,
        )
        if r.ok and r.json():
            return str(r.json()[0]["id"])
    except Exception as exc:
        print(f"  WARN could not resolve tenant for key ...{api_key[-6:]}: {exc}")
    return None


def _all_keys() -> List[str]:
    """Every key we should try: the live .env key + the persistent store."""
    keys: List[str] = []
    env_key = (os.environ.get("LANGSMITH_API_KEY") or "").strip()
    if env_key:
        keys.append(env_key)
    if KEYS_STORE.is_file():
        try:
            doc = json.loads(KEYS_STORE.read_text(encoding="utf-8"))
            for k in doc.get("keys") or []:
                k = str(k).strip()
                if k and k not in keys:
                    keys.append(k)
        except Exception as exc:
            print(f"WARN reading {KEYS_STORE.name}: {exc}")
    # De-dup preserving order.
    seen: set = set()
    out: List[str] = []
    for k in keys:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def _build_tenant_keys() -> Dict[str, str]:
    """tenant id -> API key, auto-discovered from .env + store (cached)."""
    cache: Dict[str, str] = {}
    if KEYS_CACHE.is_file():
        try:
            cache = json.loads(KEYS_CACHE.read_text(encoding="utf-8")) or {}
        except Exception:
            cache = {}
    key_to_tenant = {v: k for k, v in cache.items()}

    tenant_keys: Dict[str, str] = {}
    for key in _all_keys():
        tenant = key_to_tenant.get(key) or _resolve_tenant(key)
        if not tenant:
            continue
        tenant_keys[tenant] = key
        cache[tenant] = key
    try:
        KEYS_CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    except Exception:
        pass
    return tenant_keys


# Auto-discovered at import: tenant (org) id -> API key that can read it.
# Reads still work even if a key hit its monthly *write* (trace) cap.
TENANT_KEYS: Dict[str, str] = _build_tenant_keys()

# Agents whose v2/v3 prompts are exact copies of v1 -> only report v1.
V1_ONLY_AGENTS = frozenset({"chat_policy_block", "hallucination_guard_retry"})

_TENANT_RE = re.compile(r"/o/([0-9a-f-]+)/")


def _load_pricing() -> Dict[str, Dict[str, float]]:
    doc = yaml.safe_load(PRICING_PATH.read_text(encoding="utf-8")) or {}
    return doc.get("pricing") or {}


def _tenant_of(url: str) -> Optional[str]:
    m = _TENANT_RE.search(url or "")
    return m.group(1) if m else None


def _load_experiments() -> List[Dict[str, Any]]:
    if not CKPT_PATH.is_file():
        raise SystemExit(f"No checkpoint at {CKPT_PATH}")
    ckpt = json.loads(CKPT_PATH.read_text(encoding="utf-8"))
    rows = list((ckpt.get("completed") or {}).values())
    rows.sort(key=lambda r: (r.get("agent_id", ""), r.get("prompt_version", ""), r.get("model", "")))
    return rows


def _client_for(tenant: str):
    from langsmith import Client

    key = TENANT_KEYS.get(tenant)
    if not key:
        return None
    return Client(api_url=LANGSMITH_ENDPOINT, api_key=key)


def _example_map(client, ds_name: str) -> Dict[str, Dict[str, Any]]:
    """reference_example_id -> {inputs, gold, variation, tags, dataset_item_id}."""
    ds = client.read_dataset(dataset_name=ds_name)
    out: Dict[str, Dict[str, Any]] = {}
    for ex in client.list_examples(dataset_id=ds.id):
        meta = getattr(ex, "metadata", None) or {}
        out[str(ex.id)] = {
            "inputs": getattr(ex, "inputs", {}) or {},
            "gold": getattr(ex, "outputs", {}) or {},
            "variation": meta.get("variation", meta.get("difficulty", "unknown")),
            "tags": meta.get("tags", []),
            "dataset_item_id": meta.get("id"),
        }
    return out


def _feedback_for_runs(client, run_ids: List[str]) -> Dict[str, Dict[str, Dict[str, Any]]]:
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
        print(f"    WARN list_feedback failed: {exc}")
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
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
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
    for e in getattr(run, "events", None) or []:
        if not isinstance(e, dict) or e.get("name") != "new_token":
            continue
        ts = _parse_ts(e.get("time"))
        if ts is None:
            continue
        try:
            sa = start if start.tzinfo else start.replace(tzinfo=timezone.utc)
            ta = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
            return round((ta - sa).total_seconds(), 3)
        except Exception:
            return None
    return None


def _num(value) -> Optional[float]:
    try:
        return float(value)
    except Exception:
        return None


def _flat(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value


def collect() -> Dict[str, Any]:
    experiments = _load_experiments()
    pricing = _load_pricing()

    # Drop v2/v3 for the duplicate-prompt agents.
    kept: List[Dict[str, Any]] = []
    dropped_v23 = 0
    for exp in experiments:
        if exp.get("agent_id") in V1_ONLY_AGENTS and exp.get("prompt_version") != "v1":
            dropped_v23 += 1
            continue
        kept.append(exp)
    experiments = kept
    print(f"Experiments to export: {len(experiments)} (dropped {dropped_v23} v2/v3 copies)")

    clients: Dict[str, Any] = {}
    example_cache: Dict[Tuple[str, str], Dict[str, Dict[str, Any]]] = {}
    detailed_rows: List[Dict[str, Any]] = []
    summary_rows: List[Dict[str, Any]] = []
    skipped: List[str] = []

    for exp in experiments:
        agent_id = exp.get("agent_id")
        exp_name = exp.get("experiment_name")
        version = exp.get("prompt_version")
        provider = exp.get("provider")
        model = exp.get("model")
        tenant = _tenant_of(exp.get("langsmith_url", ""))
        if not exp_name or not agent_id:
            continue
        if tenant not in TENANT_KEYS:
            skipped.append(f"{exp_name} (no key for tenant {tenant})")
            continue

        if tenant not in clients:
            clients[tenant] = _client_for(tenant)
        client = clients[tenant]
        if client is None:
            skipped.append(f"{exp_name} (client init failed)")
            continue

        try:
            spec = get_agent_spec(agent_id)
            input_keys = spec.input_keys
            output_keys = spec.output_keys
        except Exception:
            input_keys, output_keys = [], []

        ds_name = dataset_name(agent_id)
        cache_key = (tenant, agent_id)
        if cache_key not in example_cache:
            try:
                example_cache[cache_key] = _example_map(client, ds_name)
            except Exception as exc:
                print(f"    WARN dataset read failed for {ds_name}@{tenant}: {exc}")
                example_cache[cache_key] = {}
        examples = example_cache[cache_key]

        try:
            system_prompt, _ = get_prompt_parts(agent_id, version)
        except Exception:
            system_prompt = ""

        rates = pricing.get(model) or {}
        in_rate = float(rates.get("input_per_1m_usd", 0.0)) / 1_000_000
        out_rate = float(rates.get("output_per_1m_usd", 0.0)) / 1_000_000

        print(f"  [{tenant[:8]}] {exp_name} ...")
        try:
            roots = list(client.list_runs(project_name=exp_name, is_root=True))
        except Exception as exc:
            skipped.append(f"{exp_name} (list_runs failed: {exc})")
            continue
        run_ids = [str(r.id) for r in roots]
        feedback = _feedback_for_runs(client, run_ids)

        eval_keys: List[str] = []
        for fb in feedback.values():
            for k in fb:
                if k not in eval_keys:
                    eval_keys.append(k)

        score_acc: Dict[str, List[float]] = {k: [] for k in eval_keys}
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
                pred = {"output": pred}

            try:
                _sys, user_rendered = render_prompts(agent_id, version, inputs)
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
                "agent_id": agent_id,
                "dataset_name": ds_name,
                "workspace_tenant": tenant,
                "experiment_name": exp_name,
                "prompt_version": version,
                "provider": provider,
                "model": model,
                "input_schema": ",".join(input_keys),
                "output_schema": ",".join(output_keys),
                "example_id": ex.get("dataset_item_id") or ref_id,
                "reference_example_id": ref_id,
                "run_id": rid,
                "variation": ex.get("variation"),
                "tags": "|".join(str(t) for t in (ex.get("tags") or [])),
                "input_json": json.dumps(inputs, ensure_ascii=False),
                "system_prompt": system_prompt,
                "user_prompt_rendered": user_rendered,
            }
            for k in input_keys:
                row[f"input_{k}"] = _flat(inputs.get(k))
            for k in output_keys:
                row[f"gold_{k}"] = _flat(gold.get(k))
            row["gold_json"] = json.dumps(gold, ensure_ascii=False)
            for k in output_keys:
                row[f"pred_{k}"] = _flat(pred.get(k))
            row["pred_json"] = json.dumps(pred, ensure_ascii=False)

            ex_scores: List[float] = []
            for k in eval_keys:
                sc = run_fb.get(k, {}).get("score")
                row[f"score_{k}"] = sc
                row[f"comment_{k}"] = run_fb.get(k, {}).get("comment")
                n = _num(sc)
                if n is not None:
                    score_acc[k].append(n)
                    ex_scores.append(n)
            row["example_mean_score"] = round(sum(ex_scores) / len(ex_scores), 4) if ex_scores else None

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
        means = {k: (round(sum(v) / len(v), 4) if v else None) for k, v in score_acc.items()}
        all_scores = [s for v in score_acc.values() for s in v]
        overall = round(sum(all_scores) / len(all_scores), 4) if all_scores else 0.0

        srow: Dict[str, Any] = {
            "agent_id": agent_id,
            "experiment_name": exp_name,
            "workspace_tenant": tenant,
            "prompt_version": version,
            "provider": provider,
            "model": model,
            "n_examples": n,
            "overall_mean_score": overall,
            "total_prompt_tokens": tot_pt,
            "total_completion_tokens": tot_ct,
            "total_tokens": tot_pt + tot_ct,
            "total_cost_usd": round(tot_cost, 6),
            "avg_cost_per_example_usd": round(tot_cost / n, 8) if n else None,
            "avg_latency_seconds": round(sum(latencies) / len(latencies), 3) if latencies else None,
            "avg_ttft_seconds": round(sum(ttfts) / len(ttfts), 3) if ttfts else None,
            "elapsed_seconds": exp.get("elapsed_seconds"),
            "is_winner": False,
        }
        for k in eval_keys:
            srow[f"mean_{k}"] = means.get(k)
        summary_rows.append(srow)

    # Per-agent winner: highest overall mean, tiebreak by lower cost.
    by_agent: Dict[str, List[Dict[str, Any]]] = {}
    for s in summary_rows:
        by_agent.setdefault(s["agent_id"], []).append(s)
    winners: Dict[str, str] = {}
    for aid, rows in by_agent.items():
        w = max(rows, key=lambda r: (r.get("overall_mean_score") or 0, -(r.get("total_cost_usd") or 0)))
        w["is_winner"] = True
        winners[aid] = w["experiment_name"]
    for r in detailed_rows:
        r["is_winner_experiment"] = winners.get(r["agent_id"]) == r["experiment_name"]

    return {"detailed": detailed_rows, "summary": summary_rows, "skipped": skipped, "winners": winners}


def _write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        print(f"WARN no rows for {path.name}")
        return
    fieldnames: List[str] = []
    for r in rows:
        for k in r.keys():
            if k not in fieldnames:
                fieldnames.append(k)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    print(f"Wrote {len(rows)} rows -> {path}")


def main() -> int:
    argparse.ArgumentParser().parse_args()
    data = collect()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    _write_csv(REPORTS_DIR / f"full_report_detailed_{ts}.csv", data["detailed"])
    _write_csv(REPORTS_DIR / f"full_report_summary_{ts}.csv", data["summary"])

    per_agent_dir = REPORTS_DIR / "per_agent"
    by_agent: Dict[str, List[Dict[str, Any]]] = {}
    for r in data["detailed"]:
        by_agent.setdefault(r["agent_id"], []).append(r)
    for aid, rows in by_agent.items():
        _write_csv(per_agent_dir / f"{aid}_detailed_{ts}.csv", rows)

    print("\n=== WINNERS (per agent) ===")
    for aid, exp in sorted(data["winners"].items()):
        print(f"  {aid}: {exp}")
    if data["skipped"]:
        print("\n=== SKIPPED ===")
        for s in data["skipped"]:
            print(f"  {s}")
    print(f"\nAgents exported: {len(by_agent)} | detailed rows: {len(data['detailed'])} | experiments: {len(data['summary'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
