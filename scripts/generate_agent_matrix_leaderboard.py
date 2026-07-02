#!/usr/bin/env python3
"""Generate leaderboard JSON from agent_eval step checkpoint (partial or complete)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evals.agent_eval.config import PROMPT_VERSIONS, get_langsmith_project
from evals.agent_eval.run_matrix import (
    REPORTS_DIR,
    STEP_CHECKPOINT,
    _build_plan,
    _experiment_key,
    _write_leaderboard,
)
from evals.agent_eval.registry import list_scope_agents


def main() -> int:
    if not STEP_CHECKPOINT.is_file():
        print(f"No checkpoint at {STEP_CHECKPOINT}")
        return 1
    ckpt = json.loads(STEP_CHECKPOINT.read_text(encoding="utf-8"))
    completed = ckpt.get("completed", {})
    plan = _build_plan(list_scope_agents(), list(PROMPT_VERSIONS))
    _write_leaderboard(get_langsmith_project(), plan, completed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
