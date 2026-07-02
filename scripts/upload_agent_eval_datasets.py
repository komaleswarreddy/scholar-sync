#!/usr/bin/env python3
"""Upload LangSmith datasets for agent_eval scope (14 agents) + intent_classifier."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evals.agent_eval.registry import list_scope_agents

UPLOAD_AGENTS = list(list_scope_agents()) + ["intent_classifier"]


def main() -> int:
    for agent_id in UPLOAD_AGENTS:
        print(f"\n=== Uploading {agent_id} ===")
        rc = subprocess.call(
            [sys.executable, str(ROOT / "scripts" / "upload_prompt_tiered_to_langsmith.py"), "--agent", agent_id, "--force"],
            cwd=str(ROOT),
        )
        if rc != 0:
            print(f"FAILED: {agent_id}")
            return rc
    print(f"\nAll {len(UPLOAD_AGENTS)} datasets uploaded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
