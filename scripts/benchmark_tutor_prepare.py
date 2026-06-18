#!/usr/bin/env python3
"""
Benchmark tutor notebook prepare endpoint (unified pipeline).

Usage:
  python scripts/benchmark_tutor_prepare.py
  python scripts/benchmark_tutor_prepare.py --warm
  python scripts/benchmark_tutor_prepare.py --cold --base-url http://127.0.0.1:8000

Requires API running locally. Uses dev JWT when CLERK is not configured.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.smoke_chat_flow import make_dev_jwt  # noqa: E402


ECONOMICS_CH3_SCOPE = {
    "class_num": 10,
    "subject_key": "economics",
    "subject_slug": "economics",
    "subsubject": None,
    "chapter_no": 3,
    "chapter_title": "Money and Credit",
    "filter_chapter_name": "money and credit",
    "concept": None,
}


def _assert_prepare_body(body: dict, *, max_total_ms: int) -> None:
    assert "## Summary" in (body.get("opening_summary") or ""), "missing ## Summary"
    suggestions = body.get("suggestions") or []
    assert len(suggestions) >= 3, f"expected >=3 suggestions, got {len(suggestions)}"

    recs = body.get("studio_recommendations") or []
    assert len(recs) == 4, f"expected 4 studio recommendations, got {len(recs)}"
    auto_count = sum(1 for r in recs if r.get("auto_generate"))
    assert auto_count == 2, f"expected 2 auto_generate, got {auto_count}"

    assets_created = int(body.get("assets_created") or 0)
    assert assets_created >= 1, "expected at least 1 studio asset"
    assert len(body.get("assets") or []) == assets_created

    timing = body.get("timing") or {}
    total_ms = int(timing.get("total_ms") or 0)
    print(
        json.dumps(
            {
                "timing": timing,
                "assets_created": assets_created,
                "auto_types": body.get("auto_types"),
                "slug": body.get("slug"),
            },
            indent=2,
        )
    )
    assert total_ms <= max_total_ms, f"total_ms {total_ms} exceeds budget {max_total_ms}"


def run_benchmark(
    *,
    base_url: str,
    token: str,
    warm: bool,
    max_total_ms: int,
) -> int:
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(base_url=base_url, headers=headers, timeout=180.0) as client:
        if warm:
            print("[warm] prefetch NCERT context …")
            wr = client.post(
                "/api/v1/tutor/ncert-context/warm",
                json={"tutor_scope": ECONOMICS_CH3_SCOPE},
            )
            wr.raise_for_status()
            print(wr.json())

        payload = {
            "title": "Ch. 3 · Money and Credit",
            "class_level": "Class 12",
            "subject": "Economics",
            "focus": "Ch. 3 · Money and Credit",
            "tutor_scope": ECONOMICS_CH3_SCOPE,
        }

        t0 = time.perf_counter()
        r = client.post("/api/v1/tutor/notebooks/prepare", json=payload)
        wall_ms = int((time.perf_counter() - t0) * 1000)
        print(f"[prepare] http_status={r.status_code} wall_ms={wall_ms}")
        r.raise_for_status()
        body = r.json()
        _assert_prepare_body(body, max_total_ms=max_total_ms)
        print(f"OK prepare completed within budget ({max_total_ms}ms)")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark tutor notebook prepare")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--warm", action="store_true", help="Warm NCERT cache before prepare")
    parser.add_argument("--cold", action="store_true", help="Skip warm; use cold cache budget")
    parser.add_argument("--max-ms", type=int, default=None, help="Override total_ms budget")
    args = parser.parse_args()

    max_total_ms = args.max_ms
    if max_total_ms is None:
        max_total_ms = 60_000 if args.warm else 75_000

    token = make_dev_jwt()
    try:
        return run_benchmark(
            base_url=args.base_url.rstrip("/"),
            token=token,
            warm=args.warm,
            max_total_ms=max_total_ms,
        )
    except AssertionError as exc:
        print(f"ASSERT FAIL: {exc}", file=sys.stderr)
        return 1
    except httpx.HTTPError as exc:
        print(f"HTTP FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
