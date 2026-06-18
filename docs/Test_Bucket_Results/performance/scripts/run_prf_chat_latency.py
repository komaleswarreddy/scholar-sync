#!/usr/bin/env python3
"""
PRF-01 / PRF-02 — Chat TTFT and end-to-end latency.

Usage:
  PRF_ATTEST_NO_RESTART=1 python scripts/run_prf_chat_latency.py --smoke
  PRF_ATTEST_NO_RESTART=1 python scripts/run_prf_chat_latency.py --full
  PRF_ATTEST_NO_RESTART=1 python scripts/run_prf_chat_latency.py --baseline-only
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.helpers.auth import make_dev_jwt  # noqa: E402
from tests.helpers.performance_client import CHAT_QUESTIONS, stream_chat_timed  # noqa: E402
from tests.helpers.performance_stats import (  # noqa: E402
    FailureTag,
    build_prf_report,
    collect_environment,
    compare_baseline,
    detect_pool_exhaustion,
    error_rate,
    load_baseline,
    percentiles,
    require_no_restart_attestation,
    update_baseline,
    write_prf_report,
)

THRESHOLDS_SMOKE = {
    "ttft_p95_ms": 5000.0,
    "e2e_p95_ms": 15000.0,
}
THRESHOLDS_PDF = {
    "ttft_p95_ms": 3000.0,
    "e2e_p95_ms": 8000.0,
}

COLD_START_COUNT = 3


def _resolve_source_id(base_url: str, token: str, source_id: Optional[str]) -> str:
    if source_id:
        return source_id
    env_id = os.getenv("CLASSROOM_CHAT_SOURCE_ID", "").strip()
    if env_id:
        return env_id
    fixtures = ROOT / "tests" / "fixtures" / "ingestion" / "standard_chapter.pdf"
    from tests.helpers.ingest_client import upload_file, wait_for_source_status

    with httpx.Client(base_url=base_url, timeout=180.0) as client:
        up = upload_file(client, base_url=base_url, token=token, file_path=fixtures, title="prf_chat_source")
        up.raise_for_status()
        sid = up.json()["id"]
        wait_for_source_status(client, base_url=base_url, token=token, source_id=sid)
        return sid


def _run_one(
    base_url: str,
    token: str,
    source_id: str,
    question: str,
    idx: int,
) -> Dict[str, Any]:
    with httpx.Client(base_url=base_url, timeout=180.0) as client:
        result = stream_chat_timed(
            client,
            base_url=base_url,
            token=token,
            message=question,
            active_source_ids=[source_id],
        )
    return {
        "idx": idx,
        "ttft_ms": result.ttft_ms,
        "e2e_ms": result.e2e_ms,
        "error": result.error,
        "http_status": result.http_status,
        "tokens_in": result.tokens_in,
        "tokens_out": result.tokens_out,
        "cost_usd": result.cost_usd,
        "cold_start": idx < COLD_START_COUNT,
    }


def run_chat_latency(
    *,
    base_url: str,
    n_requests: int,
    concurrency: int,
    smoke: bool,
    source_id: Optional[str] = None,
    baseline_only: bool = False,
    record_baseline: bool = False,
) -> Dict[str, Any]:
    require_no_restart_attestation()
    token = make_dev_jwt("ing_test_user_a")
    source_id = _resolve_source_id(base_url, token, source_id)
    thresholds = THRESHOLDS_SMOKE if smoke else THRESHOLDS_PDF

    t0 = time.time()
    samples: List[Dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [
            pool.submit(
                _run_one,
                base_url,
                token,
                source_id,
                CHAT_QUESTIONS[i % len(CHAT_QUESTIONS)],
                i,
            )
            for i in range(n_requests)
        ]
        for fut in concurrent.futures.as_completed(futures):
            samples.append(fut.result())

    duration_s = time.time() - t0
    warmed = [s for s in samples if not s.get("cold_start")]
    cold = [s for s in samples if s.get("cold_start")]
    errors = [s for s in warmed if s.get("error")]
    error_text = " ".join(str(s.get("error", "")) for s in samples)

    ttft_vals = [float(s["ttft_ms"]) for s in warmed if s.get("ttft_ms") is not None and not s.get("error")]
    e2e_vals = [float(s["e2e_ms"]) for s in warmed if s.get("e2e_ms") is not None and not s.get("error")]

    ttft_pct = percentiles(ttft_vals)
    e2e_pct = percentiles(e2e_vals)
    cold_ttft = percentiles([float(s["ttft_ms"]) for s in cold if s.get("ttft_ms") is not None and not s.get("error")])
    cold_e2e = percentiles([float(s["e2e_ms"]) for s in cold if s.get("e2e_ms") is not None and not s.get("error")])

    total_cost = sum(float(s["cost_usd"] or 0) for s in warmed if s.get("cost_usd") is not None)
    err_rate = error_rate(len(errors), len(warmed) or 1)

    failure_tags: List[str] = []
    status = "PASS"

    if detect_pool_exhaustion(error_text):
        failure_tags.append(FailureTag.OPEN_BUG.value)
        status = "OPEN_BUG"
    elif err_rate >= 0.01:
        failure_tags.append(FailureTag.ERROR_SPIKE.value)
        status = "FAIL"
    elif ttft_pct.get("p95", 0) > thresholds["ttft_p95_ms"]:
        failure_tags.append(FailureTag.LATENCY.value)
        status = "FAIL"
    elif e2e_pct.get("p95", 0) > thresholds["e2e_p95_ms"]:
        failure_tags.append(FailureTag.LATENCY.value)
        status = "FAIL"

    if smoke and status == "FAIL" and failure_tags == [FailureTag.LATENCY.value]:
        status = "XFAIL"

    metrics = {
        "percentiles": True,
        "ttft_ms": ttft_pct,
        "e2e_ms": e2e_pct,
        "cold_start": {"ttft_ms": cold_ttft, "e2e_ms": cold_e2e},
        "error_rate": err_rate,
        "errors": len(errors),
        "total_cost_usd": total_cost,
        "concurrency": concurrency,
        "thresholds": thresholds,
        "mode": "smoke" if smoke else "pdf",
    }

    if baseline_only:
        status = "BASELINE"

    report = build_prf_report(
        test_ids=["PRF-01", "PRF-02"],
        status=status,
        metrics=metrics,
        environment=collect_environment(),
        failure_tags=failure_tags,
        duration_s=duration_s,
        sample_size=len(warmed),
    )
    out_path = ROOT / "evals" / "reports" / "prf_chat_latency.json"
    write_prf_report(report, out_path)
    write_prf_report(report)

    baseline = load_baseline()
    if baseline:
        warnings = compare_baseline(
            {"ttft_ms": ttft_pct.get("p95"), "e2e_ms": e2e_pct.get("p95"), "cost_usd": total_cost},
            baseline.get("metrics", {}).get("summary", {}),
        )
        if warnings:
            print("Baseline regression warnings:", warnings)

    if baseline_only or record_baseline:
        update_baseline(report)

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="PRF-01/02 chat latency runner")
    parser.add_argument("--smoke", action="store_true", help="Smoke mode (20 req, relaxed thresholds)")
    parser.add_argument("--full", action="store_true", help="Full PDF mode (200 req, strict thresholds)")
    parser.add_argument("--baseline-only", action="store_true", help="Record baseline only")
    parser.add_argument("--record-baseline", action="store_true", help="Save report as prf_baseline.json after run")
    parser.add_argument("--n", type=int, default=0, help="Override request count")
    parser.add_argument("--concurrency", type=int, default=0, help="Override concurrency")
    parser.add_argument("--source-id", default="", help="Pre-indexed source id")
    parser.add_argument("--base-url", default=os.getenv("NOTEBOOKLM_API_URL", "http://127.0.0.1:8000"))
    args = parser.parse_args()

    smoke = args.smoke or (not args.full and not args.n)
    n = args.n or (20 if smoke else 200)
    concurrency = args.concurrency or (5 if smoke else 10)

    try:
        report = run_chat_latency(
            base_url=args.base_url,
            n_requests=n,
            concurrency=concurrency,
            smoke=smoke,
            source_id=args.source_id or None,
            baseline_only=args.baseline_only,
            record_baseline=args.record_baseline,
        )
    except RuntimeError as exc:
        print(f"PRF guardrail blocked run: {exc}")
        return 2

    print(json.dumps(report.get("metrics", {}), indent=2))
    print(f"Status: {report.get('status')}")
    return 0 if report.get("status") in {"PASS", "BASELINE", "XFAIL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
