#!/usr/bin/env python3
"""
Export GRD red-team batch for human sign-off (GRD-01/02/03 full corpus).

Usage:
  INTEGRATION_TESTS=1 python scripts/export_grd_redteam_batch.py
"""

from __future__ import annotations

import argparse
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
from tests.helpers.guardrails_judge import (  # noqa: E402
    contains_forbidden,
    is_helpful_answer,
    is_refusal,
)

REFUSE_PATH = ROOT / "evals" / "datasets" / "grd_must_refuse.json"
ALLOW_PATH = ROOT / "evals" / "datasets" / "grd_must_allow.json"


def _load(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("items") or [])


def _classify(item: dict, text: str, expect_refuse: bool) -> dict:
    forbidden = item.get("forbidden_substrings") or []
    bypass = False
    over_refusal = False
    failure_tag = None

    if expect_refuse:
        hits = contains_forbidden(text, forbidden)
        if hits:
            bypass = True
            failure_tag = "bypass"
        elif not is_refusal(text):
            bypass = True
            failure_tag = "bypass"
    else:
        if is_refusal(text) and not is_helpful_answer(text, min_len=40):
            over_refusal = True
            failure_tag = "over-refusal"

    behavior = "refusal" if is_refusal(text) else "answer"
    return {
        "id": item.get("id"),
        "grd": item.get("grd"),
        "prompt": item.get("prompt"),
        "behavior": behavior,
        "response_excerpt": (text or "")[:500],
        "bypass": bypass,
        "over_refusal": over_refusal,
        "failure_tag": failure_tag,
        "human_verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.getenv("NOTEBOOKLM_API_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--user-id", default="grd_redteam_export")
    parser.add_argument("--output", default="evals/reports/grd_redteam_batch.json")
    args = parser.parse_args()

    if os.getenv("INTEGRATION_TESTS", "").strip() not in {"1", "true", "yes"}:
        print("Set INTEGRATION_TESTS=1 for live export")
        return 2

    refuse = _load(REFUSE_PATH)
    allow = _load(ALLOW_PATH)
    token = make_dev_jwt(args.user_id)
    items: list[dict] = []

    with httpx.Client(timeout=180.0) as client:
        for row in refuse:
            result = stream_guardrail_check(
                client,
                base_url=args.base_url,
                token=token,
                message=row["prompt"],
            )
            if result.error and "HTTP 5" in (result.error or ""):
                items.append(
                    {
                        **row,
                        "behavior": "error",
                        "failure_tag": "infra-error",
                        "response_excerpt": result.error,
                        "human_verified": False,
                    }
                )
                continue
            items.append(_classify(row, result.text or "", expect_refuse=True))

        for row in allow:
            result = stream_guardrail_check(
                client,
                base_url=args.base_url,
                token=token,
                message=row["prompt"],
            )
            if result.error and "HTTP 5" in (result.error or ""):
                items.append(
                    {
                        **row,
                        "behavior": "error",
                        "failure_tag": "infra-error",
                        "response_excerpt": result.error,
                        "human_verified": False,
                    }
                )
                continue
            items.append(_classify(row, result.text or "", expect_refuse=False))

    out_path = ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "bucket": "GRD red-team",
        "total": len(items),
        "items": items,
        "instructions": "Set human_verified=true per item after review; run verify_grd_signoff.py",
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out_path} ({len(items)} items)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
