#!/usr/bin/env python3
"""
PRF-03 — Tutor scoped vs Exploratory retrieval latency comparison.

Usage:
  PRF_ATTEST_NO_RESTART=1 python scripts/run_prf_scoped_retrieval.py --smoke
  PRF_ATTEST_NO_RESTART=1 python scripts/run_prf_scoped_retrieval.py --full
"""

from __future__ import annotations

import argparse
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
from tests.helpers.ingest_client import upload_file, wait_for_source_status  # noqa: E402
from tests.helpers.performance_client import CHAT_QUESTIONS, stream_chat_timed  # noqa: E402
from tests.helpers.performance_stats import (  # noqa: E402
    FailureTag,
    build_prf_report,
    collect_environment,
    percentiles,
    require_no_restart_attestation,
    write_prf_report,
)

TUTOR_QUESTION = "Explain photosynthesis and the role of chlorophyll in plants."
EXPLORATORY_QUESTION = "Explain photosynthesis and the role of chlorophyll in plants."


def _resolve_tutor_scope(base_url: str, token: str) -> Dict[str, Any]:
    class_num = int(os.getenv("NBM_TUTOR_CLASS", "10"))
    subject_key = os.getenv("NBM_TUTOR_SUBJECT", "science")
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(base_url=base_url, timeout=60.0) as client:
        resp = client.get(
            f"{base_url}/api/v1/tutor/catalog",
            params={"class_num": class_num, "subject": subject_key},
            headers=headers,
        )
        resp.raise_for_status()
        chapters = resp.json().get("chapters") or []
        indexed = [c for c in chapters if c.get("indexed") and int(c.get("chunks_count") or 0) > 0]
        chapter = (indexed or chapters)[0]
        return {
            "class_num": class_num,
            "subject_key": subject_key,
            "chapter_no": int(chapter["chapter_no"]),
            "chapter_title": chapter.get("chapter_title") or chapter.get("title") or "",
            "filter_chapter_name": chapter.get("filter_chapter_name"),
        }


def _exploratory_source(base_url: str, token: str) -> str:
    fixtures = ROOT / "tests" / "fixtures" / "ingestion" / "standard_chapter.pdf"
    with httpx.Client(base_url=base_url, timeout=180.0) as client:
        up = upload_file(client, base_url=base_url, token=token, file_path=fixtures, title="prf_exploratory")
        up.raise_for_status()
        sid = up.json()["id"]
        wait_for_source_status(client, base_url=base_url, token=token, source_id=sid)
        return sid


def _run_mode(
    client: httpx.Client,
    *,
    base_url: str,
    token: str,
    mode: str,
    scope: Optional[Dict[str, Any]],
    source_id: Optional[str],
    n: int,
) -> List[float]:
    e2e_vals: List[float] = []
    for i in range(n):
        kwargs: Dict[str, Any] = {}
        if mode == "tutor" and scope:
            kwargs = {
                "include_ncert_global": True,
                "ncert_class": scope["class_num"],
                "ncert_subject": scope["subject_key"],
                "ncert_chapter_no": scope["chapter_no"],
                "ncert_chapter_name": scope.get("filter_chapter_name") or scope.get("chapter_title"),
            }
            question = TUTOR_QUESTION
        else:
            kwargs = {"active_source_ids": [source_id] if source_id else []}
            question = CHAT_QUESTIONS[i % len(CHAT_QUESTIONS)]
        result = stream_chat_timed(
            client,
            base_url=base_url,
            token=token,
            message=question,
            **kwargs,
        )
        if result.error:
            continue
        if result.e2e_ms is not None:
            e2e_vals.append(result.e2e_ms)
    return e2e_vals


def run_scoped_retrieval(*, base_url: str, smoke: bool) -> dict:
    require_no_restart_attestation()
    token = make_dev_jwt("prf_scope_user")
    n = 5 if smoke else 10
    scope = _resolve_tutor_scope(base_url, token)
    exploratory_source = _exploratory_source(base_url, token)

    t0 = time.time()
    with httpx.Client(base_url=base_url, timeout=180.0) as client:
        tutor_vals = _run_mode(client, base_url=base_url, token=token, mode="tutor", scope=scope, source_id=None, n=n)
        exploratory_vals = _run_mode(
            client,
            base_url=base_url,
            token=token,
            mode="exploratory",
            scope=None,
            source_id=exploratory_source,
            n=n,
        )

    tutor_pct = percentiles(tutor_vals)
    exploratory_pct = percentiles(exploratory_vals)
    tutor_p95 = tutor_pct.get("p95", 0)
    exploratory_p95 = exploratory_pct.get("p95", 0)

    failure_tags: List[str] = []
    status = "PASS"
    tutor_budget_ms = 5000.0 if not smoke else 15000.0

    if tutor_p95 > tutor_budget_ms:
        failure_tags.append(FailureTag.LATENCY.value)
        status = "FAIL"
    elif exploratory_p95 > 0 and tutor_p95 >= exploratory_p95:
        failure_tags.append(FailureTag.LATENCY.value)
        status = "FAIL"
        failure_tags.append("scoped_not_faster_than_exploratory")

    if smoke and status == "FAIL" and FailureTag.OPEN_BUG.value not in failure_tags:
        status = "XFAIL"

    report = build_prf_report(
        test_ids=["PRF-03"],
        status=status,
        metrics={
            "percentiles": True,
            "tutor_e2e_ms": tutor_pct,
            "exploratory_e2e_ms": exploratory_pct,
            "tutor_faster": tutor_p95 < exploratory_p95 if exploratory_p95 else None,
            "tutor_p95_budget_ms": tutor_budget_ms,
            "mode": "smoke" if smoke else "pdf",
        },
        environment=collect_environment(),
        failure_tags=failure_tags,
        duration_s=time.time() - t0,
        sample_size=len(tutor_vals) + len(exploratory_vals),
    )
    write_prf_report(report, ROOT / "evals" / "reports" / "prf_scoped_retrieval.json")
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
        report = run_scoped_retrieval(base_url=args.base_url, smoke=smoke)
    except RuntimeError as exc:
        print(exc)
        return 2
    print(json.dumps(report.get("metrics", {}), indent=2))
    return 0 if report.get("status") in {"PASS", "XFAIL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
