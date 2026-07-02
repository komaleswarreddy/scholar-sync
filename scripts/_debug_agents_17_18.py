#!/usr/bin/env python3
"""Sample empty/partial runs for agents 17/18."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from langsmith import Client
from evals.agent_eval.evaluator_loader import parse_model_response

KEY = "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"
client = Client(api_key=KEY)

cases = [
    ("explain_from_basics", "ae-explain_from_basics-v3-anthropic-claude-sonnet-4-6"),
    ("explain_from_basics", "ae-explain_from_basics-v1-gemini-gemini-3-5-flash"),
    ("show_best_approach", "ae-show_best_approach-v3-anthropic-claude-sonnet-4-6"),
]

for agent, prefix in cases:
    projs = sorted(client.list_projects(name_contains=prefix), key=lambda p: p.name, reverse=True)
    if not projs:
        print("missing", prefix)
        continue
    proj = projs[0]
    print("\n===", proj.name, "===")
    runs = list(client.list_runs(project_id=str(proj.id), is_root=True, limit=3))
    for r in runs:
        if isinstance(r.outputs, dict) and r.outputs:
            continue
        print("empty example", getattr(r, "error", None))
        kids = list(client.list_runs(project_id=str(proj.id), filter=f'eq(parent_run_id, "{r.id}")', limit=5))
        for c in kids:
            raw = (c.outputs or {}).get("text") if isinstance(c.outputs, dict) else None
            if raw is not None:
                print(" raw len", len(raw), "tail", repr(raw[-180:]))
                print(" parsed", bool(parse_model_response(agent, raw)))
                print(" err", c.error)
                break
            if c.error:
                print(" child err", str(c.error)[:200])
