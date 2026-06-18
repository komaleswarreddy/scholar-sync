#!/usr/bin/env python3
"""End-to-end workflow evaluation CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from packages.core.evaluation.e2e.workflow import run_e2e_evaluation


def main() -> int:
  parser = argparse.ArgumentParser(description="ScholarSync E2E workflow evaluation")
  parser.add_argument("--limit", type=int, default=10, help="Number of workflow samples")
  parser.add_argument("--project", default="notebooklm-dev", help="LangSmith project")
  args = parser.parse_args()

  report = run_e2e_evaluation(limit=args.limit, project=args.project)
  print(json.dumps(report, indent=2))
  return 0 if report.get("passed") else 1


if __name__ == "__main__":
  raise SystemExit(main())
