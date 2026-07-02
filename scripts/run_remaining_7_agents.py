#!/usr/bin/env python3
"""Run remaining agent evals with automatic LangSmith workspace rotation."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
LEDGER_PATH = ROOT / "evals" / "reports" / "agent_matrix" / "trace_ledger.json"
CACHE_PATH = ROOT / "evals" / "reports" / "agent_matrix" / "workspace_keys_cache.json"
EXHAUSTED_PATH = ROOT / "evals" / "reports" / "agent_matrix" / "exhausted_workspaces.json"

# Rotation order: fresher workspaces first (cursemes9/eskomal66 likely exhausted).
WORKSPACE_ROTATION = [
    ("gra7399", "67272628-c819-44db-bbda-e500db0d6982"),
    ("sui332307", "33d88f33-0349-4117-89c6-5d0d56252773"),
    ("pscmrmindssprint2k25", "15d476d5-df92-4760-96b8-52f9130946bf"),
    ("scombinator26", "47ca8a69-43eb-4f05-812b-c7778fe6987d"),
    ("emaildam3", "aafff4b5-45a3-4448-9f7d-805bfc70098d"),
    ("gra7399", "67272628-c819-44db-bbda-e500db0d6982"),
    ("sui332307", "33d88f33-0349-4117-89c6-5d0d56252773"),
    ("eskomal66", "03ba6fa5-eb21-4c9a-9eab-fbf8c26ad03b"),
    ("cursemes9", "ac6f370c-8fcd-46f3-a85c-b5cd59a9f2e7"),
]

REMAINING_AGENTS = [
    "tutor_follow_up_questions",
]


def _load_cache() -> dict[str, str]:
    if not CACHE_PATH.exists():
        return {}
    return json.loads(CACHE_PATH.read_text(encoding="utf-8"))


def _load_exhausted() -> set[str]:
    if not EXHAUSTED_PATH.exists():
        return set()
    try:
        return set(json.loads(EXHAUSTED_PATH.read_text(encoding="utf-8")))
    except Exception:
        return set()


def _save_exhausted(tenants: set[str]) -> None:
    EXHAUSTED_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXHAUSTED_PATH.write_text(json.dumps(sorted(tenants), indent=2), encoding="utf-8")


def _archive_ledger(label: str) -> None:
    if not LEDGER_PATH.exists():
        return
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = LEDGER_PATH.parent / f"trace_ledger_{label}_{ts}.json"
    shutil.copy2(LEDGER_PATH, dest)
    fresh = {
        "month": datetime.now(timezone.utc).strftime("%Y-%m"),
        "limit": 5000,
        "safety_margin": 250,
        "used": 0,
        "experiments": [],
        "workspace_tenant": label,
        "note": f"Fresh ledger after workspace switch ({label})",
    }
    LEDGER_PATH.write_text(json.dumps(fresh, indent=2), encoding="utf-8")


def _patch_env(api_key: str) -> None:
    text = ENV_PATH.read_text(encoding="utf-8")
    text = re.sub(r"^LANGSMITH_API_KEY=.*$", f"LANGSMITH_API_KEY={api_key}", text, flags=re.MULTILINE)
    # Re-enable all providers; use Claude judge now that credits are restored.
    text = re.sub(r"^AGENT_EVAL_JUDGE_MODEL=.*$", "AGENT_EVAL_JUDGE_MODEL=gpt-4o", text, flags=re.MULTILINE)
    if "AGENT_EVAL_JUDGE_MODEL=" not in text:
        text += "\nAGENT_EVAL_JUDGE_MODEL=gpt-4o\n"
    for skip_var in ("AGENT_EVAL_SKIP_OPENAI", "AGENT_EVAL_SKIP_ANTHROPIC"):
        text = re.sub(rf"^{skip_var}=.*\n?", "", text, flags=re.MULTILINE)
    ENV_PATH.write_text(text, encoding="utf-8")


def _switch_workspace(name: str, tenant: str, key: str) -> None:
    label = f"{name}_{tenant[:8]}"
    _archive_ledger(label)
    _patch_env(key)
    cache = _load_cache()
    cache[tenant] = key
    CACHE_PATH.write_text(json.dumps(cache, indent=2) + "\n", encoding="utf-8")
    print(f"\n>>> Switched workspace -> {name} ({tenant})")


def _upload_agents(agents: list[str]) -> None:
    for agent_id in agents:
        print(f"Uploading dataset: {agent_id}...")
        subprocess.run(
            [sys.executable, "scripts/upload_prompt_tiered_to_langsmith.py", "--force", "--agent", agent_id],
            cwd=ROOT,
            check=False,
        )


def _run_matrix(agents: list[str]) -> int:
    cmd = [sys.executable, "-m", "evals.agent_eval.run_matrix", "--all"]
    for a in agents:
        cmd.extend(["--agent", a])
    print(f"\n>>> Running matrix: {' '.join(agents)}")
    return subprocess.run(cmd, cwd=ROOT).returncode


def _pending_experiments(agents: list[str]) -> int:
    """Count pending without Gemini health probes (fast)."""
    sys.path.insert(0, str(ROOT))
    from evals.agent_eval.config import PROMPT_VERSIONS, get_agent_models

    ckpt_path = ROOT / "evals" / "reports" / "agent_matrix" / "step_checkpoint.json"
    completed: dict = {}
    if ckpt_path.exists():
        try:
            completed = json.loads(ckpt_path.read_text(encoding="utf-8")).get("completed", {})
        except Exception:
            pass
    pending = 0
    for agent_id in agents:
        for pv in PROMPT_VERSIONS:
            for spec in get_agent_models(agent_id):
                key = f"{agent_id}::{pv}::{spec.provider}::{spec.model}"
                row = completed.get(key)
                if row and row.get("status") != "error":
                    continue
                pending += 1
    return pending


def main() -> int:
    cache = _load_cache()
    exhausted = _load_exhausted()

    pending = _pending_experiments(REMAINING_AGENTS)
    if pending == 0:
        print("All remaining agent experiments complete.")
        return 0
    print(f"Pending experiments: {pending}")

    for name, tenant in WORKSPACE_ROTATION:
        if tenant in exhausted:
            print(f"Skipping exhausted workspace: {name}")
            continue
        key = cache.get(tenant)
        if not key:
            print(f"No API key for {name} ({tenant}) — skip")
            continue

        _switch_workspace(name, tenant, key)
        _upload_agents(REMAINING_AGENTS)
        code = _run_matrix(REMAINING_AGENTS)

        pending = _pending_experiments(REMAINING_AGENTS)
        if pending == 0:
            print("\nAll remaining experiments complete.")
            return 0
        if code == 2:
            print(f"Trace limit hit on {name} — rotating...")
            exhausted.add(tenant)
            _save_exhausted(exhausted)
            continue
        if code != 0:
            print(f"Matrix exited with code {code}; {pending} experiments still pending.")
            return code

    print(f"All workspaces exhausted or unavailable. {pending} experiments still pending.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
