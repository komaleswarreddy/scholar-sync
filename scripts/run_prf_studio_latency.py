#!/usr/bin/env python3
"""
PRF-05 — Studio generation P95 by task type.

Usage:
  PRF_ATTEST_NO_RESTART=1 python scripts/run_prf_studio_latency.py --smoke
  PRF_ATTEST_NO_RESTART=1 python scripts/run_prf_studio_latency.py --full
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.helpers.auth import make_dev_jwt  # noqa: E402
from tests.helpers.ingest_client import upload_file, wait_for_source_status  # noqa: E402
from tests.helpers.performance_client import generate_studio_timed  # noqa: E402
from tests.helpers.performance_stats import (  # noqa: E402
    FailureTag,
    build_prf_report,
    collect_environment,
    percentiles,
    require_no_restart_attestation,
    write_prf_report,
)

TASK_TYPES = ["quiz", "flashcards", "mind_map", "slide_deck"]
THRESHOLDS_PDF_MS = {
    "quiz": 12000.0,
    "flashcards": 10000.0,
    "mind_map": 15000.0,
    "slide_deck": 20000.0,
}


def _source_id(base_url: str, token: str) -> str:
    sid = os.getenv("CLASSROOM_CHAT_SOURCE_ID", "").strip()
    if sid:
        return sid
    fixtures = ROOT / "tests" / "fixtures" / "ingestion" / "standard_chapter.pdf"
    with httpx.Client(base_url=base_url, timeout=180.0) as client:
        up = upload_file(client, base_url=base_url, token=token, file_path=fixtures, title="prf_studio_source")
        up.raise_for_status()
        source_id = up.json()["id"]
        wait_for_source_status(client, base_url=base_url, token=token, source_id=source_id)
        return source_id


def run_studio(*, base_url: str, smoke: bool) -> dict:
    require_no_restart_attestation()
    token = make_dev_jwt("ing_test_user_a")
    source_id = _source_id(base_url, token)
    n_per_type = 1 if smoke else int(os.getenv("PRF_STUDIO_N_PER_TYPE", "5"))
    t0 = time.time()
    per_type: Dict[str, List[float]] = {t: [] for t in TASK_TYPES}
    errors: List[str] = []
    failure_tags: List[str] = []
    status = "PASS"

    with httpx.Client(base_url=base_url, timeout=300.0) as client:
        for task_type in TASK_TYPES:
            threshold = THRESHOLDS_PDF_MS[task_type] * (2.0 if smoke else 1.0)
            for _ in range(n_per_type):
                result = generate_studio_timed(
                    client,
                    base_url=base_url,
                    token=token,
                    task_type=task_type,
                    source_ids=[source_id],
                )
                if result.error or result.status_code >= 400:
                    errors.append(f"{task_type}: {result.error or result.status_code}")
                    if result.status_code >= 500:
                        failure_tags.append(FailureTag.OPEN_BUG.value)
                        status = "OPEN_BUG"
                    continue
                if result.e2e_ms is not None:
                    per_type[task_type].append(result.e2e_ms)
            pct = percentiles(per_type[task_type])
            if pct.get("p95", 0) > threshold and status == "PASS":
                failure_tags.append(FailureTag.LATENCY.value)
                status = "FAIL"

    metrics = {
        "percentiles": True,
        "per_type_ms": {t: percentiles(v) for t, v in per_type.items()},
        "thresholds_ms": {t: THRESHOLDS_PDF_MS[t] * (2.0 if smoke else 1.0) for t in TASK_TYPES},
        "errors": len(errors),
        "mode": "smoke" if smoke else "pdf",
    }
    report = build_prf_report(
        test_ids=["PRF-05"],
        status=status,
        metrics=metrics,
        environment=collect_environment(),
        failure_tags=list(set(failure_tags)),
        duration_s=time.time() - t0,
        sample_size=sum(len(v) for v in per_type.values()),
    )
    write_prf_report(report, ROOT / "evals" / "reports" / "prf_studio_latency.json")
    write_prf_report(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--base-url", default=os.getenv("NOTEBOOKLM_API_URL", "http://127.0.0.1:8000"))
    args = parser.parse_args()
    smoke = args.smoke or not args.full
    try:
        report = run_studio(base_url=args.base_url, smoke=smoke)
    except RuntimeError as exc:
        print(exc)
        return 2
    print(json.dumps(report.get("metrics", {}), indent=2))
    return 0 if report.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
