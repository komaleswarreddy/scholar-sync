#!/usr/bin/env python3
"""Check in_reject_set for all cached LangSmith workspaces."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

CACHE_PATH = ROOT / "evals" / "reports" / "agent_matrix" / "workspace_keys_cache.json"
NAMES = {
    "15d476d5-df92-4760-96b8-52f9130946bf": "pscmrmindssprint2k25",
    "47ca8a69-43eb-4f05-812b-c7778fe6987d": "scombinator26",
    "aafff4b5-45a3-4448-9f7d-805bfc70098d": "emaildam3",
    "67272628-c819-44db-bbda-e500db0d6982": "gra7399",
    "33d88f33-0349-4117-89c6-5d0d56252773": "sui332307",
    "03ba6fa5-eb21-4c9a-9eab-fbf8c26ad03b": "eskomal66",
    "ac6f370c-8fcd-46f3-a85c-b5cd59a9f2e7": "cursemes9",
}

endpoint = (os.environ.get("LANGSMITH_ENDPOINT") or "https://api.smith.langchain.com").rstrip("/")
cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))

print(f"{'Workspace':<22} {'reject_set':<12} {'tenant_limit':<14} active_key")
print("-" * 70)
active = (os.environ.get("LANGSMITH_API_KEY") or "").strip()
for tid, key in cache.items():
    name = NAMES.get(tid, tid[:8])
    marker = " <-- ACTIVE" if key == active else ""
    try:
        resp = requests.get(
            f"{endpoint}/api/v1/workspaces/current/usage_limits",
            headers={"x-api-key": key},
            timeout=15,
        )
        if resp.ok:
            data = resp.json()
            print(
                f"{name:<22} {str(data.get('in_reject_set')):<12} "
                f"{str(data.get('tenant_limit')):<14}{marker}"
            )
        else:
            print(f"{name:<22} HTTP {resp.status_code}{marker}")
    except Exception as exc:
        print(f"{name:<22} ERR {exc}{marker}")
