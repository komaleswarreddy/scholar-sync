#!/usr/bin/env python3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from langsmith import Client
from packages.core.evaluation.datasets.loader import load_agent_dataset

KEY = "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"
client = Client(api_key=KEY)
records = {str(r.id): r for r in load_agent_dataset("help_me_solve_it")}
by_ex_id = {r.id: r for r in load_agent_dataset("help_me_solve_it")}

for prefix in (
    "ae-help_me_solve_it-v3-openai-gpt-5-4",
    "ae-help_me_solve_it-v1-openai-gpt-5-4",
):
    proj = sorted(client.list_projects(name_contains=prefix), key=lambda p: p.name, reverse=True)[0]
    ic_empty = Counter()
    ic_ok = Counter()
    for r in client.list_runs(project_id=str(proj.id), is_root=True, limit=50):
        meta = getattr(r, "metadata", None) or {}
        ex_id = meta.get("dataset_example_id") or getattr(r, "reference_example_id", None)
        ic = "?"
        for rec in by_ex_id.values():
            if str(getattr(rec, "langsmith_id", "")) == str(ex_id) or rec.id == ex_id:
                ic = rec.input.get("interaction_count", "?")
                break
        if isinstance(r.outputs, dict) and r.outputs:
            ic_ok[ic] += 1
        else:
            ic_empty[ic] += 1
    print(prefix)
    print("  ok by ic", dict(ic_ok))
    print("  empty by ic", dict(ic_empty))
