#!/usr/bin/env python3
"""Export CSF probe responses for human review."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from tests.helpers.auth import make_dev_jwt  # noqa: E402
from tests.helpers.guardrails_client import stream_guardrail_check  # noqa: E402
from tests.helpers.csf_judge import (  # noqa: E402
    is_empathetic_pressure_response,
    is_grooming_safe_route,
    is_over_trigger_crisis,
    is_supportive_distress_response,
)
from tests.helpers.guardrails_judge import is_refusal  # noqa: E402

DATASETS = [
    "csf_distress_probes.json",
    "csf_manipulation_probes.json",
    "csf_pressure_probes.json",
    "csf_grooming_probes.json",
    "csf_must_treat_normally.json",
]
OUT = ROOT / "evals" / "reports" / "csf_human_review_batch.json"
BASE_URL = os.getenv("NOTEBOOKLM_API_URL", "http://127.0.0.1:8000")


def _load_items(name: str) -> list[dict]:
    path = ROOT / "evals" / "datasets" / name
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("items") or [])


def _judge(item: dict, text: str) -> dict:
    expect = item.get("expect") or ""
    out = {"expect": expect, "is_refusal": is_refusal(text)}
    if expect == "supportive_route":
        out["supportive_ok"] = is_supportive_distress_response(
            text, item.get("supportive_markers") or []
        )
    elif expect == "refuse_cheating":
        out["refusal_ok"] = is_refusal(text)
        out["empathy_ok"] = is_empathetic_pressure_response(
            text, item.get("supportive_markers") or []
        )
    elif expect == "allow_study":
        out["over_trigger"] = is_over_trigger_crisis(text)
    if item.get("csf") == "CSF-06" or "csf-g-" in item.get("id", ""):
        out["grooming_safe"] = is_grooming_safe_route(
            text, item.get("forbidden_substrings") or []
        )
    return out


def main() -> int:
    token = make_dev_jwt("csf_export_runner")
    rows: list[dict] = []
    with httpx.Client(base_url=BASE_URL, timeout=120.0) as client:
        client.headers["Authorization"] = f"Bearer {token}"
        if client.get("/health").status_code != 200:
            print("API unhealthy")
            return 2
        for ds in DATASETS:
            for item in _load_items(ds):
                result = stream_guardrail_check(
                    client,
                    base_url=BASE_URL,
                    token=token,
                    message=item["prompt"],
                    active_source_ids=[],
                )
                text = result.text or ""
                rows.append(
                    {
                        "dataset": ds,
                        "id": item.get("id"),
                        "csf": item.get("csf"),
                        "prompt": item["prompt"],
                        "response": text[:4000],
                        "human_verified": False,
                        "auto_judge": _judge(item, text),
                    }
                )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"items": rows}, indent=2), encoding="utf-8")
    print(f"Wrote {len(rows)} rows to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
