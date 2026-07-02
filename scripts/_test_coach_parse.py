#!/usr/bin/env python3
"""Test lenient coach JSON parser against live LangSmith gemini output."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from langsmith import Client
from evals.agent_eval.evaluator_loader import parse_model_response

KEY = "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"
client = Client(api_key=KEY)
proj = sorted(
    client.list_projects(name_contains="ae-explain_from_basics-v1-gemini-gemini-3-5-flash"),
    key=lambda p: p.name,
    reverse=True,
)[0]
runs = list(client.list_runs(project_id=str(proj.id), is_root=True, limit=30))
for r in runs:
    if isinstance(r.outputs, dict) and r.outputs:
        continue
    kids = list(
        client.list_runs(
            project_id=str(proj.id),
            filter=f'eq(parent_run_id, "{r.id}")',
            limit=5,
        )
    )
    for c in kids:
        raw = (c.outputs or {}).get("text") if isinstance(c.outputs, dict) else None
        if raw:
            out = parse_model_response("explain_from_basics", raw)
            ok = bool(out.get("coach_json"))
            print("parsed", ok, "sections", len((out.get("coach_json") or {}).get("sections", [])))
            sys.exit(0 if ok else 1)
print("no empty sample found")
sys.exit(1)
