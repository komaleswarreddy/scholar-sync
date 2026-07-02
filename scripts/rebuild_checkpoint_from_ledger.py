#!/usr/bin/env python3
"""Rebuild step_checkpoint.json completed keys from trace_ledger.json (dedupe by agent/prompt/model)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "evals" / "reports" / "agent_matrix" / "trace_ledger.json"
CHECKPOINT = ROOT / "evals" / "reports" / "agent_matrix" / "step_checkpoint.json"

PROVIDER_MAP = {
    "gpt-": "openai",
    "claude-": "anthropic",
    "gemini-": "gemini",
}


def infer_provider(model: str) -> str:
    m = model.lower()
    for prefix, prov in PROVIDER_MAP.items():
        if m.startswith(prefix):
            return prov
    return "unknown"


def exp_key(agent_id: str, prompt_version: str, model: str) -> str:
    prov = infer_provider(model)
    return f"{agent_id}::{prompt_version}::{prov}::{model}"


def main() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    completed = {}
    seen = set()
    for row in ledger.get("experiments", []):
        k = exp_key(row["agent_id"], row["prompt_version"], row["model"])
        if k in seen:
            continue
        seen.add(k)
        prov = infer_provider(row["model"])
        completed[k] = {
            "agent_id": row["agent_id"],
            "experiment_prefix": f"ae-{row['agent_id']}-{row['prompt_version']}-{prov}-{row['model']}".replace(".", "-"),
            "prompt_version": row["prompt_version"],
            "provider": prov,
            "model": row["model"],
            "experiment_name": row["experiment_name"],
            "traces_this_experiment": row.get("charged_traces", row.get("estimated_traces", 0)),
            "status": "ok",
        }
    ckpt = {
        "completed": completed,
        "started_at": ledger.get("updated_at", ""),
        "updated_at": ledger.get("updated_at", ""),
        "rebuilt_from": "trace_ledger.json",
    }
    CHECKPOINT.write_text(json.dumps(ckpt, indent=2), encoding="utf-8")
    print(f"Rebuilt checkpoint: {len(completed)} unique experiments")
    for k in sorted(completed):
        print(f"  [x] {k}")


if __name__ == "__main__":
    main()
