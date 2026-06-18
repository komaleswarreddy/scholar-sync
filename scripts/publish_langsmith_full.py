#!/usr/bin/env python3
"""
Full LangSmith publish: datasets + experiments + e2e + visibility report.

Publishes to LANGSMITH_PROJECT from .env (default notebooklm-dev).

Usage:
  python scripts/publish_langsmith_full.py
  python scripts/publish_langsmith_full.py --limit 5 --agents intent_classifier,query_rewriter
  python scripts/publish_langsmith_full.py --skip-upload --skip-experiments
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from packages.core.evaluation.datasets.loader import load_manifest
from packages.core.evaluation.e2e.workflow import run_e2e_evaluation
from packages.core.evaluation.experiments.runner import run_experiment
from packages.core.observability.langsmith_publish import ensure_tracing, get_langsmith_project


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish full eval visibility to LangSmith")
    parser.add_argument("--limit", type=int, default=5, help="Examples per agent experiment")
    parser.add_argument("--agents", default=None, help="Comma-separated agent ids; default all 33")
    parser.add_argument("--skip-upload", action="store_true")
    parser.add_argument("--skip-experiments", action="store_true")
    parser.add_argument("--skip-e2e", action="store_true")
    parser.add_argument("--start-api", action="store_true", help="Start uvicorn in background")
    parser.add_argument("--mock", action="store_true", help="Use mock outputs instead of live LLM")
    parser.add_argument("--skip-comparison-md", action="store_true", help="Skip comparison markdown generation")
    args = parser.parse_args()

    status = ensure_tracing()
    project = get_langsmith_project()
    print(f"LangSmith project: {project} | enabled: {status.get('enabled')}")

    if not status.get("enabled"):
        print("ERROR: LangSmith not enabled. Set LANGSMITH_TRACING_ENABLED=true and LANGSMITH_API_KEY in .env")
        return 1

    if args.start_api:
        subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "apps.api.main:app", "--port", "8000"],
            cwd=str(ROOT),
        )
        print("Started API on :8000")

    manifest = load_manifest()
    agent_ids = (
        [a.strip() for a in args.agents.split(",") if a.strip()]
        if args.agents
        else [ds["dataset_id"] for ds in manifest.get("datasets") or []]
    )

    upload_summary = None
    if not args.skip_upload:
        print("\n=== Step 1: Upload datasets ===")
        cmd = [sys.executable, str(ROOT / "scripts" / "upload_prompt_tiered_to_langsmith.py")]
        if args.agents:
            for aid in agent_ids:
                subprocess.run(cmd + ["--agent", aid], check=False)
        else:
            subprocess.run(cmd, check=False)
        up_path = ROOT / "evals" / "reports" / "langsmith_datasets_upload.json"
        if up_path.is_file():
            upload_summary = json.loads(up_path.read_text(encoding="utf-8"))

    experiment_summaries = []
    batch_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    live = not args.mock
    if not args.skip_experiments:
        print(f"\n=== Step 2: Run experiments + publish runs/feedback (live={live}) ===")
        for aid in agent_ids:
            print(f"  Experiment: {aid} (limit={args.limit})")
            try:
                report = run_experiment(
                    aid,
                    limit=args.limit,
                    publish_to_langsmith=True,
                    live=live,
                    eval_batch_id=batch_id,
                )
                experiment_summaries.append({
                    "agent": aid,
                    "score": report["rows"][0]["score"] if report.get("rows") else 0,
                    "passed": report["rows"][0]["passed"] if report.get("rows") else False,
                    "langsmith_runs": report.get("langsmith_example_runs", 0),
                    "evaluator": report.get("evaluator"),
                    "dataset_hash": report.get("dataset_hash"),
                })
            except Exception as exc:
                experiment_summaries.append({"agent": aid, "error": str(exc)})

    e2e_report = None
    if not args.skip_e2e:
        print("\n=== Step 3: E2E workflow eval ===")
        e2e_report = run_e2e_evaluation(limit=min(args.limit, 10), project=project)

    checklist = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "langsmith_project": project,
        "langsmith_url": f"https://smith.langchain.com",
        "visibility_checklist": {
            "datasets_visible": f"Datasets tab -> nbm-prompt-* ({len(agent_ids)} agents)",
            "example_inputs_outputs": "Each dataset example has inputs + reference_outputs",
            "evaluator_metadata": "On each example: evaluator, variation, tags in metadata",
            "experiment_runs": "Tracing -> Runs named eval/{agent}/{example_id}",
            "experiment_summaries": "Tracing -> Runs named experiment/{agent}/{prompt}/{model}",
            "feedback_scores": "Feedback on runs: weighted_score, passed, metric_*, total_cost_usd",
            "cost_breakdown": "Run metadata: input_cost_usd, output_cost_usd, prompt_tokens, completion_tokens",
            "model_and_prompt": "Run metadata: model, prompt_version, agent_name",
            "e2e_workflow": "Tracing -> Run e2e/workflow_evaluation",
            "live_agent_traces": "Chat API -> intent_classifier runs with token/cost metadata",
        },
        "upload": upload_summary,
        "experiments": experiment_summaries,
        "e2e": e2e_report,
        "local_reports": [
            "evals/reports/langsmith_datasets_upload.json",
            "evals/reports/experiment_*.json",
            "evals/reports/e2e_workflow_latest.json",
            "evals/reports/langsmith_visibility_report.json",
        ],
    }

    out = ROOT / "evals" / "reports" / "langsmith_visibility_report.json"
    out.write_text(json.dumps(checklist, indent=2), encoding="utf-8")

    if not args.skip_comparison_md:
        print("\n=== Step 4: Generate comparison markdown ===")
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "generate_comparison_report.py")],
            check=False,
        )

    print(f"\n=== Done ===")
    print(f"Visibility report: {out}")
    print(f"Open LangSmith project: {project}")
    print(json.dumps({"agents": len(agent_ids), "experiments": len(experiment_summaries)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
