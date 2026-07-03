#!/usr/bin/env python3
"""Full combo status audit for agents 17-19 across LangSmith workspaces."""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from langsmith import Client

from evals.agent_eval.config import PROMPT_VERSIONS, get_agent_models

# tenant_id -> api_key (org id in URLs may differ from tenant id)
WORKSPACES = {
    "604dd9bc-eacc-48c9-8352-648bb1d715fa": ("royalrowdy13", "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"),
    "d28c3c60-acaf-4c17-af45-a056921cdb06": ("komaleswarreddy", "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"),
    "9fced417-9e4c-442f-bcda-d11a78caaec8": ("citizena45", "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"),
    "ac6f370c-8fcd-46f3-a85c-b5cd59a9f2e7": ("cursemes9", "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"),
}

AGENTS = {
    "explain_from_basics": {"sno": 17, "expected": 30, "primary_tenant": "604dd9bc-eacc-48c9-8352-648bb1d715fa"},
    "show_best_approach": {"sno": 18, "expected": 30, "primary_tenant": "d28c3c60-acaf-4c17-af45-a056921cdb06"},
    "show_missing_idea": {"sno": 19, "expected": 30, "primary_tenant": "9fced417-9e4c-442f-bcda-d11a78caaec8"},
}

ORG_URL_ID = {
    "9fced417-9e4c-442f-bcda-d11a78caaec8": "fd0bc6a5-5f75-4225-9c2e-1b10708f0b8c",
}


def stats(client: Client, session_id: str) -> tuple[int, int, int, str]:
    ok = err = empty = 0
    sample = ""
    offset = 0
    while True:
        batch = list(client.list_runs(project_id=session_id, is_root=True, limit=100, offset=offset))
        if not batch:
            break
        for r in batch:
            if r.error:
                err += 1
                if not sample:
                    sample = str(r.error)[:120]
            elif isinstance(r.outputs, dict) and r.outputs:
                ok += 1
            else:
                empty += 1
        if len(batch) < 100:
            break
        offset += len(batch)
    return ok, err, empty, sample


def parse_combo(name: str, models: list[str]) -> tuple[str, str] | None:
    pv = model = None
    for p in PROMPT_VERSIONS:
        if f"-{p}-" in name:
            pv = p
            break
    for m in models:
        if m.replace(".", "-") in name or m in name:
            model = m
            break
    if pv and model:
        return pv, model
    return None


def audit_agent(agent_id: str) -> dict:
    meta = AGENTS[agent_id]
    models = [s.model for s in get_agent_models(agent_id)]
    best: dict[tuple[str, str], dict] = {}

    for tenant, (label, key) in WORKSPACES.items():
        try:
            client = Client(api_key=key)
        except Exception as e:
            continue
        prefix = f"ae-{agent_id}-"
        try:
            projects = list(client.list_projects(name_contains=prefix))
        except Exception as e:
            print(f"  [{label}] API error: {e}", file=sys.stderr)
            continue
        for proj in projects:
            combo = parse_combo(proj.name, models)
            if not combo:
                continue
            ok, err, empty, sample = stats(client, str(proj.id))
            total = ok + err + empty
            row = {
                "workspace": label,
                "tenant": tenant,
                "pv": combo[0],
                "model": combo[1],
                "ok": ok,
                "err": err,
                "empty": empty,
                "total_runs": total,
                "fill": f"{ok}/{meta['expected']}",
                "session_id": str(proj.id),
                "experiment": proj.name,
                "sample_error": sample,
            }
            key_c = combo
            prev = best.get(key_c)
            if prev is None or ok > prev["ok"] or (ok == prev["ok"] and empty < prev["empty"]):
                best[key_c] = row

    return {"agent_id": agent_id, "meta": meta, "models": models, "combos": best}


def main() -> int:
    all_results = []
    for agent_id in AGENTS:
        result = audit_agent(agent_id)
        all_results.append(result)
        meta = result["meta"]
        print("=" * 100)
        print(f"AGENT {meta['sno']}: {agent_id} (expected {meta['expected']}/combo)")
        print("=" * 100)
        full = partial = empty_combo = not_run = 0
        for pv in PROMPT_VERSIONS:
            for model in result["models"]:
                row = result["combos"].get((pv, model))
                if not row:
                    not_run += 1
                    print(f"  [MISSING] {pv}/{model} | no experiment found")
                    continue
                ok, exp = row["ok"], meta["expected"]
                if row["err"] > 0:
                    status = "ERROR"
                elif ok == exp and row["empty"] == 0:
                    status = "FULL"
                    full += 1
                elif ok == 0:
                    status = "EMPTY"
                    empty_combo += 1
                else:
                    status = "PARTIAL"
                    partial += 1
                org = ORG_URL_ID.get(row["tenant"], row["tenant"])
                print(
                    f"  [{status}] {pv}/{model} | {row['fill']} fill | "
                    f"err={row['err']} empty={row['empty']} | ws={row['workspace']} | "
                    f"{row['experiment']}"
                )
        print(
            f"  SUMMARY: FULL={full}/9 PARTIAL={partial} EMPTY={empty_combo} "
            f"NOT_RUN={not_run} (of {len(PROMPT_VERSIONS)*len(result['models'])} combos)"
        )
        print()

    out = ROOT / "evals/reports/agent_matrix/audit_agents_17_18_19.json"
    out.write_text(json.dumps(all_results, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
