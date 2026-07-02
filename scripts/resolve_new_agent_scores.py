#!/usr/bin/env python3
"""Resolve overall mean quality scores for the 7 newest agents via LangSmith API.

The 14 matrix agents + intent_classifier already have scores in their full_report
summary CSVs; only these 7 need API resolution. Writes a JSON score cache keyed
by experiment_name. Reads only — no trace quota consumed.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

from langsmith import Client

PROGRESS_DIR = ROOT / "evals" / "reports" / "agent_eval_progress"
LINKS_PATH = PROGRESS_DIR / "agent_eval_experiment_links_20260630T134011Z.csv"
CACHE_PATH = PROGRESS_DIR / "new_agent_score_cache.json"
TENANT_CACHE = json.loads((ROOT / "evals/reports/agent_matrix/workspace_keys_cache.json").read_text())

NEW_AGENTS = {
    "problem_dna_analyzer",
    "whole_file_reduce",
    "whole_file_map_summarizer",
    "explain_from_basics",
    "show_best_approach",
    "show_missing_idea",
    "ncert_document_sketch",
}
ENDPOINT = "https://api.smith.langchain.com"


def resolve_score(client, experiment_name: str) -> float | None:
    try:
        roots = list(client.list_runs(project_name=experiment_name, is_root=True))
        if not roots:
            return None
        run_ids = [str(r.id) for r in roots]
        scores: list[float] = []
        # list_feedback caps run_ids batches; chunk to stay under API limits.
        for start in range(0, len(run_ids), 100):
            batch = run_ids[start : start + 100]
            for fb in client.list_feedback(run_ids=batch):
                key = fb.key or ""
                if fb.score is None or key.endswith("severity_summary") or key == "severity_tier_summary":
                    continue
                try:
                    scores.append(float(fb.score))
                except Exception:
                    pass
        return round(sum(scores) / len(scores), 4) if scores else None
    except Exception as exc:
        print(f"  WARN {experiment_name}: {exc}")
        return None


def main() -> None:
    cache: dict[str, float] = {}
    if CACHE_PATH.is_file():
        cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))

    rows = list(csv.DictReader(open(LINKS_PATH, encoding="utf-8")))
    targets = [r for r in rows if r["Agent ID"] in NEW_AGENTS]
    clients: dict[str, Client] = {}
    total = len(targets)
    for i, r in enumerate(targets, 1):
        exp = r["Experiment Name"]
        tenant = r["Workspace Tenant"]
        if exp in cache:
            continue
        key = TENANT_CACHE.get(tenant)
        if not key:
            continue
        if tenant not in clients:
            clients[tenant] = Client(api_url=ENDPOINT, api_key=key)
        score = resolve_score(clients[tenant], exp)
        cache[exp] = score
        print(f"  [{i}/{total}] {exp[:55]} -> {score}")
        CACHE_PATH.write_text(json.dumps(cache, indent=2), encoding="utf-8")

    print(f"Wrote {CACHE_PATH} ({len(cache)} experiments)")


if __name__ == "__main__":
    main()
