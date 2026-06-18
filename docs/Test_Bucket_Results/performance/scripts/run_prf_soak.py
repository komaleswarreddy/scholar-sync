#!/usr/bin/env python3
"""
PRF-07 — Soak test scaffold (2–4 hours sustained moderate load).

Spawns resource sampler sidecar, runs moderate Locust load, compares start vs end latency.

Usage:
  PRF_ATTEST_NO_RESTART=1 python scripts/run_prf_soak.py
  PRF_ATTEST_NO_RESTART=1 python scripts/run_prf_soak.py --duration 2h
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.helpers.performance_stats import (  # noqa: E402
    FailureTag,
    build_prf_report,
    collect_environment,
    merge_into_latest,
    require_no_restart_attestation,
    write_prf_report,
)

REPORTS = ROOT / "evals" / "reports"
RESOURCE_OUT = REPORTS / "prf_resource_timeseries.jsonl"
RESOURCE_SUMMARY = REPORTS / "prf_resource_timeseries.summary.json"


def _parse_duration(s: str) -> float:
    s = s.strip().lower()
    if s.endswith("h"):
        return float(s[:-1]) * 3600.0
    if s.endswith("m"):
        return float(s[:-1]) * 60.0
    return float(s)


def run_soak(*, base_url: str, duration_s: float, interval_s: float = 30.0) -> Dict[str, Any]:
    require_no_restart_attestation()
    t0 = time.time()

    sampler_cmd = [
        sys.executable,
        "scripts/prf_resource_sampler.py",
        "--duration",
        str(duration_s),
        "--interval",
        str(interval_s),
        "--out",
        str(RESOURCE_OUT),
    ]
    sampler_proc = subprocess.Popen(sampler_cmd, cwd=str(ROOT))

    env = os.environ.copy()
    env.setdefault("PRF_ATTEST_NO_RESTART", "1")
    env["PRF_WORKLOAD"] = "1"
    env["GATE_CLASSROOM_SHORT"] = "0"

    load_hours = duration_s / 3600.0
    run_time = f"{max(30, int(duration_s / 60))}m"
    users = "20" if load_hours < 3 else "30"

    load_cmd = [
        sys.executable,
        "scripts/run_prf_load.py",
        "--full",
        "--base-url",
        base_url,
    ]
    os.environ["GATE_CLASSROOM_SHORT"] = "0"
    os.environ.setdefault("PRF_ATTEST_NO_RESTART", "1")

    import importlib.util

    gate_path = ROOT / "scripts" / "run_prod_gate.py"
    spec = importlib.util.spec_from_file_location("run_prod_gate", gate_path)
    gate_mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(gate_mod)

    chat_user, chat_source_id = gate_mod.seed_classroom_chat_source(base_url)
    os.environ["CLASSROOM_CHAT_SOURCE_ID"] = chat_source_id
    os.environ["CLASSROOM_CHAT_USER"] = chat_user
    os.environ["PRF_WORKLOAD"] = "1"

    stats_prefix = REPORTS / "prf_soak_stats"
    locust_cmd = [
        sys.executable,
        "-m",
        "locust",
        "-f",
        "tests/load/locustfile_classroom.py",
        "--host",
        base_url,
        "--users",
        users,
        "--spawn-rate",
        "5",
        "--run-time",
        run_time,
        "--headless",
        "--csv",
        str(stats_prefix),
    ]

    chat_start = subprocess.run(
        [sys.executable, "scripts/run_prf_chat_latency.py", "--smoke", "--n", "5", "--concurrency", "1"],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    locust_exit = gate_mod.run(locust_cmd)
    locust_exit = gate_mod.validate_classroom_locust_result(locust_exit)
    chat_end = subprocess.run(
        [sys.executable, "scripts/run_prf_chat_latency.py", "--smoke", "--n", "5", "--concurrency", "1"],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )

    sampler_proc.wait(timeout=60)

    rss_summary: Dict[str, Any] = {}
    if RESOURCE_SUMMARY.exists():
        rss_summary = json.loads(RESOURCE_SUMMARY.read_text(encoding="utf-8"))

    failure_tags: List[str] = []
    status = "PASS"
    growth_pct = rss_summary.get("growth_pct")
    if growth_pct is not None and growth_pct > 10.0:
        failure_tags.append(FailureTag.RESOURCE_EXHAUSTION.value)
        status = "FAIL"
    if locust_exit != 0:
        failure_tags.append(FailureTag.ERROR_SPIKE.value)
        status = "FAIL"

    report = build_prf_report(
        test_ids=["PRF-07"],
        status=status,
        metrics={
            "duration_s": duration_s,
            "locust_exit_code": locust_exit,
            "rss_summary": rss_summary,
            "chat_start_exit": chat_start.returncode,
            "chat_end_exit": chat_end.returncode,
            "run_time": run_time,
            "users": users,
        },
        environment=collect_environment(),
        failure_tags=failure_tags,
        duration_s=time.time() - t0,
        notes="Manual soak: verify start vs end chat latency in prf_chat_latency.json snapshots.",
    )
    write_prf_report(report, REPORTS / "prf_soak.json")
    merge_into_latest(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", default="2h", help="Soak duration (e.g. 2h, 4h, 7200)")
    parser.add_argument("--base-url", default=os.getenv("NOTEBOOKLM_API_URL", "http://127.0.0.1:8000"))
    args = parser.parse_args()
    duration_s = _parse_duration(args.duration)

    try:
        report = run_soak(base_url=args.base_url, duration_s=duration_s)
    except RuntimeError as exc:
        print(exc)
        return 2

    print(json.dumps(report.get("metrics", {}), indent=2))
    print(f"Status: {report.get('status')}")
    return 0 if report.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
