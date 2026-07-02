#!/usr/bin/env python3
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from langsmith import Client
from evals.agent_eval.evaluator_loader import parse_model_response
from evals.datasets.final_Evalutors.explain_from_basics_evaluators import _json_from_text

KEY = "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"
client = Client(api_key=KEY)
proj = sorted(client.list_projects(name_contains="ae-explain_from_basics-v1-gemini-gemini-3-5-flash"), key=lambda p: p.name, reverse=True)[0]
runs = list(client.list_runs(project_id=str(proj.id), is_root=True, limit=30))
for r in runs:
    if isinstance(r.outputs, dict) and r.outputs:
        continue
    kids = list(client.list_runs(project_id=str(proj.id), filter=f'eq(parent_run_id, "{r.id}")', limit=5))
    for c in kids:
        raw = (c.outputs or {}).get("text") if isinstance(c.outputs, dict) else None
        if raw:
            print("len", len(raw))
            print("head", repr(raw[:120]))
            print("tail", repr(raw[-120:]))
            print("_json_from_text", bool(_json_from_text(raw)))
            print("parse_model_response", parse_model_response("explain_from_basics", raw))
            try:
                import json
                json.loads(raw)
                print("direct json.loads OK")
            except Exception as e:
                print("direct json.loads FAIL", e)
            sys.exit(0)
