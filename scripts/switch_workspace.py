#!/usr/bin/env python3
"""Switch LangSmith workspace: archive trace ledger, reset budget, update .env."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
LEDGER_PATH = ROOT / "evals" / "reports" / "agent_matrix" / "trace_ledger.json"
CACHE_PATH = ROOT / "evals" / "reports" / "agent_matrix" / "workspace_keys_cache.json"

WORKSPACES = {
    "pscmrmindssprint2k25": {
        "tenant": "15d476d5-df92-4760-96b8-52f9130946bf",
        "key": "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",
        "gmail": "pscmrmindssprint2k25@gmail.com",
    },
    "scombinator26": {
        "tenant": "47ca8a69-43eb-4f05-812b-c7778fe6987d",
        "key": "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",
        "gmail": "scombinator26@gmail.com",
    },
    "emaildam3": {
        "tenant": "aafff4b5-45a3-4448-9f7d-805bfc70098d",
        "key": "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",
        "gmail": "emaildam3@gmail.com",
    },
    "gra7399": {
        "tenant": "67272628-c819-44db-bbda-e500db0d6982",
        "key": "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",
        "gmail": "gra7399@gmail.com",
    },
    "sui332307": {
        "tenant": "33d88f33-0349-4117-89c6-5d0d56252773",
        "key": "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",
        "gmail": "sui332307@gmail.com",
    },
    "eskomal66": {
        "tenant": "03ba6fa5-eb21-4c9a-9eab-fbf8c26ad03b",
        "key": "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",
        "gmail": "eskomal66@gmail.com",
    },
    "cursemes9": {
        "tenant": "ac6f370c-8fcd-46f3-a85c-b5cd59a9f2e7",
        "key": "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",
        "gmail": "cursemes9@gmail.com",
    },
    "sujithgundala97": {
        "tenant": "bf982111-f0d4-424f-9520-3605217266b1",
        "key": "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",
        "gmail": "sujith.gundala97@gmail.com",
    },
    "kumarsujith006": {
        "tenant": "3ee9feb1-5211-4d8a-b489-69b9933538f3",
        "key": "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",
        "gmail": "kumarsujith006@gmail.com",
    },
    "citizena45": {
        "tenant": "9fced417-9e4c-442f-bcda-d11a78caaec8",
        "key": "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",
        "gmail": "citizena45@gmail.com",
    },
    "shivaprapul550": {
        "tenant": "6fb8fab2-fc02-49fb-ad42-5df052958213",
        "key": "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",
        "gmail": "shivaprapul550@gmail.com",
    },
    "shivaprapulsp": {
        "tenant": "c997e411-7986-45a4-991c-db218a869d43",
        "key": "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",
        "gmail": "shivaprapul.sp@gmail.com",
    },
    "komaleswarreddy": {
        "tenant": "d28c3c60-acaf-4c17-af45-a056921cdb06",
        "key": "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",
        "gmail": "komaleswarreddy@gmail.com",
    },
}


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


def _patch_env(api_key: str, judge_model: str) -> None:
    text = ENV_PATH.read_text(encoding="utf-8")
    text = re.sub(r"^LANGSMITH_API_KEY=.*$", f"LANGSMITH_API_KEY={api_key}", text, flags=re.MULTILINE)
    for var in ("AGENT_EVAL_JUDGE_MODEL", "INTENT_EVAL_JUDGE_MODEL"):
        if f"{var}=" in text:
            text = re.sub(rf"^{var}=.*$", f"{var}=gpt-4o", text, flags=re.MULTILINE)
        else:
            text += f"\n{var}=gpt-4o\n"
    ENV_PATH.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace", choices=list(WORKSPACES.keys()))
    parser.add_argument("--judge-model", default="gpt-4o", help="LLM judge (always gpt-4o)")
    args = parser.parse_args()
    ws = WORKSPACES[args.workspace]
    label = f"{args.workspace}_{ws['tenant'][:8]}"
    archived = _archive_ledger(label)
    _patch_env(ws["key"], "gpt-4o")
    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8")) if CACHE_PATH.exists() else {}
    cache[ws["tenant"]] = ws["key"]
    CACHE_PATH.write_text(json.dumps(cache, indent=2) + "\n", encoding="utf-8")
    print(f"Archived ledger: {archived}")
    print(f"Switched to {ws['gmail']} ({ws['tenant']})")
    print(f"Judge model: gpt-4o")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
