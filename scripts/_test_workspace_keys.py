#!/usr/bin/env python3
import json
import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
cache = json.loads((ROOT / "evals/reports/agent_matrix/workspace_keys_cache.json").read_text())
endpoint = "https://api.smith.langchain.com"
names = {
    "15d476d5-df92-4760-96b8-52f9130946bf": "pscmrmindssprint2k25",
    "47ca8a69-43eb-4f05-812b-c7778fe6987d": "scombinator26",
    "aafff4b5-45a3-4448-9f7d-805bfc70098d": "emaildam3",
    "67272628-c819-44db-bbda-e500db0d6982": "gra7399",
    "33d88f33-0349-4117-89c6-5d0d56252773": "sui332307",
    "03ba6fa5-eb21-4c9a-9eab-fbf8c26ad03b": "eskomal66",
    "ac6f370c-8fcd-46f3-a85c-b5cd59a9f2e7": "cursemes9",
    "d4bf70c1-a262-4d2d-88a7-e44e8f609e09": "extra1",
    "bf1641b0-1c4d-46e6-9a41-3d95cc3411e8": "extra2",
}
for tid, key in cache.items():
    name = names.get(tid, tid[:8])
    try:
        r = requests.get(
            f"{endpoint}/api/v1/workspaces/current/usage_limits",
            headers={"x-api-key": key},
            timeout=15,
        )
        if r.ok:
            d = r.json()
            print(f"{name:22} OK  capped={d.get('in_reject_set')}")
        else:
            print(f"{name:22} HTTP {r.status_code} {r.text[:80]}")
    except Exception as e:
        print(f"{name:22} ERR {e}")
