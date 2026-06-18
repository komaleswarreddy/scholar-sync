#!/usr/bin/env python3
"""
PRF-04 — Ingestion pipeline P95 latency.

Usage:
  PRF_ATTEST_NO_RESTART=1 python scripts/run_prf_ingestion.py --smoke
  PRF_ATTEST_NO_RESTART=1 python scripts/run_prf_ingestion.py --full --concurrent
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sys
import time
import uuid
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.helpers.auth import make_dev_jwt  # noqa: E402
from tests.helpers.performance_client import ingest_timed  # noqa: E402
from tests.helpers.performance_stats import (  # noqa: E402
    FailureTag,
    build_prf_report,
    collect_environment,
    percentiles,
    require_no_restart_attestation,
    write_prf_report,
)

THRESHOLDS_SMOKE_S = 90.0
THRESHOLDS_PDF_S = 30.0


def _make_probe(fixtures_dir: Path, pages: int, idx: int) -> Path:
    lines_per_page = 40
    content = "\n".join(
        f"PRF ingest page {p} line {l}: {uuid.uuid4()}" for p in range(pages) for l in range(lines_per_page)
    )
    path = fixtures_dir / f"_prf_ingest_{uuid.uuid4().hex}.txt"
    path.write_text(content + f"\nprobe {idx}\n", encoding="utf-8")
    return path


def run_ingestion(*, base_url: str, smoke: bool, concurrent: bool) -> dict:
    require_no_restart_attestation()
    token = make_dev_jwt("prf_ingest_user")
    fixtures_dir = ROOT / "tests" / "fixtures" / "ingestion"
    pages = 3 if smoke else 10
    n = 3 if smoke else 5
    threshold_s = THRESHOLDS_SMOKE_S if smoke else THRESHOLDS_PDF_S

    t0 = time.time()
    durations_s: list[float] = []
    errors: list[str] = []

    def _one(i: int) -> tuple[float | None, str | None]:
        probe = _make_probe(fixtures_dir, pages, i)
        try:
            with httpx.Client(base_url=base_url, timeout=300.0) as client:
                result = ingest_timed(
                    client,
                    base_url=base_url,
                    token=token,
                    file_path=probe,
                    title=f"prf_ingest_{i}",
                    timeout_s=threshold_s * 2,
                )
            if result.error:
                return None, result.error
            return (result.e2e_ms or 0) / 1000.0, None
        finally:
            probe.unlink(missing_ok=True)

    if concurrent and not smoke:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            for dur, err in pool.map(_one, range(n)):
                if err:
                    errors.append(err)
                elif dur is not None:
                    durations_s.append(dur)
    else:
        for i in range(n):
            dur, err = _one(i)
            if err:
                errors.append(err)
            elif dur is not None:
                durations_s.append(dur)

    pct = percentiles(durations_s)
    p95 = pct.get("p95", 0)
    failure_tags: list[str] = []
    status = "PASS"
    if errors:
        if any("500" in e or "max clients" in e.lower() for e in errors):
            failure_tags.append(FailureTag.OPEN_BUG.value)
            status = "OPEN_BUG"
        else:
            failure_tags.append(FailureTag.ERROR_SPIKE.value)
            status = "FAIL"
    elif p95 > threshold_s:
        failure_tags.append(FailureTag.LATENCY.value)
        status = "FAIL"

    report = build_prf_report(
        test_ids=["PRF-04"],
        status=status,
        metrics={
            "percentiles": True,
            "ingest_s": pct,
            "pages": pages,
            "concurrent": concurrent and not smoke,
            "threshold_s": threshold_s,
            "errors": len(errors),
            "mode": "smoke" if smoke else "pdf",
        },
        environment=collect_environment(),
        failure_tags=failure_tags,
        duration_s=time.time() - t0,
        sample_size=len(durations_s),
    )
    write_prf_report(report, ROOT / "evals" / "reports" / "prf_ingestion.json")
    write_prf_report(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--concurrent", action="store_true", help="Run concurrent uploads (full mode)")
    parser.add_argument("--base-url", default=os.getenv("NOTEBOOKLM_API_URL", "http://127.0.0.1:8000"))
    args = parser.parse_args()
    smoke = args.smoke or not args.full
    try:
        report = run_ingestion(base_url=args.base_url, smoke=smoke, concurrent=args.concurrent or not smoke)
    except RuntimeError as exc:
        print(exc)
        return 2
    print(json.dumps(report.get("metrics", {}), indent=2))
    return 0 if report.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
