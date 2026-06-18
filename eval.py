#!/usr/bin/env python3
"""
Agent-level evaluation CLI.

Example:
  python eval.py --agent intent_classifier --prompts v1 --models gpt-4o-mini
  python eval.py --agent intent_classifier --two-phase --limit 10
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from packages.core.evaluation.experiments.runner import run_experiment, run_two_phase_experiment
from packages.core.observability.langsmith_publish import get_langsmith_project


def main() -> int:
  parser = argparse.ArgumentParser(description="ScholarSync agent evaluation")
  parser.add_argument("--agent", required=True, help="Agent id (e.g. intent_classifier)")
  parser.add_argument("--dataset", default=None, help="Dataset id override")
  parser.add_argument("--prompts", default=None, help="Comma-separated prompt versions")
  parser.add_argument("--models", default=None, help="Comma-separated models")
  parser.add_argument("--limit", type=int, default=None, help="Max dataset examples")
  parser.add_argument("--two-phase", action="store_true", help="Run 2-phase experiment strategy")
  parser.add_argument("--project", default=None, help="LangSmith project (default: LANGSMITH_PROJECT from .env)")
  parser.add_argument("--mock", action="store_true", help="Use mock outputs instead of live LLM")
  args = parser.parse_args()

  prompts = [p.strip() for p in args.prompts.split(",")] if args.prompts else None
  models = [m.strip() for m in args.models.split(",")] if args.models else None

  project = args.project or get_langsmith_project()
  live = not args.mock

  if args.two_phase:
    report = run_two_phase_experiment(args.agent, models=models, limit=args.limit, live=live)
  else:
    report = run_experiment(
      args.agent,
      dataset=args.dataset,
      prompts=prompts,
      models=models,
      limit=args.limit,
      project=project,
      publish_to_langsmith=True,
      live=live,
    )

  print(json.dumps(report, indent=2))
  winner = report.get("winner") or (report.get("phase2") or {}).get("winner")
  if winner and winner.get("selected"):
    print(f"\nWINNER: prompt={winner['winner']['prompt']} model={winner['winner']['model']} score={winner['winner']['score']}")
    return 0
  if report.get("rows") and report["rows"][0].get("passed"):
    return 0
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
