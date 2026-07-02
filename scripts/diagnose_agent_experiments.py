#!/usr/bin/env python3
"""List all LangSmith experiments for an agent with ok/error/empty counts."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from langsmith import Client

from evals.agent_eval.config import PROMPT_VERSIONS, get_agent_models

KEYS = json.loads(
    (ROOT / "evals/reports/agent_matrix/workspace_keys_cache.json").read_text(encoding="utf-8")
)

WORKSPACE_BY_TENANT = {
    "67272628-c819-44db-bbda-e500db0d6982": "gra7399",
    "33d88f33-0349-4117-89c6-5d0d56252773": "sui332307",
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
                    sample = str(r.error)[:140]
            elif isinstance(r.outputs, dict) and r.outputs:
                ok += 1
            else:
                empty += 1
        if len(batch) < 100:
            break
        offset += len(batch)
    return ok, err, empty, sample


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", required=True)
    parser.add_argument("--tenant", required=True)
    args = parser.parse_args()

    key = KEYS[args.tenant]
    client = Client(api_key=key)
    prefix = f"ae-{args.agent}-"
    specs = {s.model: s for s in get_agent_models(args.agent)}

    print(f"Agent: {args.agent} | tenant: {args.tenant} ({WORKSPACE_BY_TENANT.get(args.tenant, '?')})")
    print("-" * 100)
    projects = sorted(client.list_projects(name_contains=prefix), key=lambda p: p.name)
    for proj in projects:
        name = proj.name
        sid = str(proj.id)
        ok, err, empty, sample = stats(client, sid)
        pv = model = "?"
        for p in PROMPT_VERSIONS:
            if f"-{p}-" in name:
                pv = p
                break
        for m in specs:
            if m.replace(".", "-") in name or m in name:
                model = m
                break
        flag = "OK" if err == 0 and ok > 0 and empty == 0 else "BAD"
        print(f"[{flag}] {pv}/{model} | ok={ok} err={err} empty={empty} | {name}")
        if sample:
            print(f"       sample_error: {sample}")


if __name__ == "__main__":
    main()
