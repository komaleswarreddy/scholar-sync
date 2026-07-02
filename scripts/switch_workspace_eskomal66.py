#!/usr/bin/env python3
"""Switch LangSmith workspace: archive trace ledger, update .env API key."""

from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
LEDGER_PATH = ROOT / "evals" / "reports" / "agent_matrix" / "trace_ledger.json"
CACHE_PATH = ROOT / "evals" / "reports" / "agent_matrix" / "workspace_keys_cache.json"

ESKOMAL_TENANT = "03ba6fa5-eb21-4c9a-9eab-fbf8c26ad03b"
ESKOMAL_KEY = "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"
CURSEMES9_TENANT = "ac6f370c-8fcd-46f3-a85c-b5cd59a9f2e7"
CURSEMES9_KEY = "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"


def _archive_ledger(label: str) -> Path | None:
    if not LEDGER_PATH.exists():
        return None
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
        "note": f"Fresh ledger after switching workspace ({label})",
    }
    LEDGER_PATH.write_text(json.dumps(fresh, indent=2), encoding="utf-8")
    return dest


def _patch_env(api_key: str) -> None:
    text = ENV_PATH.read_text(encoding="utf-8")
    text = re.sub(
        r"^LANGSMITH_API_KEY=.*$",
        f"LANGSMITH_API_KEY={api_key}",
        text,
        flags=re.MULTILINE,
    )
    if "AGENT_EVAL_JUDGE_MODEL=" in text:
        text = re.sub(
            r"^AGENT_EVAL_JUDGE_MODEL=.*$",
            "AGENT_EVAL_JUDGE_MODEL=gpt-4o",
            text,
            flags=re.MULTILINE,
        )
    else:
        text += "\nAGENT_EVAL_JUDGE_MODEL=gpt-4o\n"
    ENV_PATH.write_text(text, encoding="utf-8")


def _update_cache() -> None:
    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8")) if CACHE_PATH.exists() else {}
    cache[ESKOMAL_TENANT] = ESKOMAL_KEY
    cache[CURSEMES9_TENANT] = CURSEMES9_KEY
    CACHE_PATH.write_text(json.dumps(cache, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    archived = _archive_ledger("eskomal66_03ba6fa5")
    _patch_env(ESKOMAL_KEY)
    _update_cache()
    print(f"Archived ledger: {archived}")
    print(f"Switched .env LANGSMITH_API_KEY -> eskomal66 ({ESKOMAL_TENANT})")
    print("Set AGENT_EVAL_JUDGE_MODEL=gpt-4o")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
