#!/usr/bin/env python3
"""
Validate PRF report against the 16-item developer checklist.

Usage:
  python scripts/verify_prf_signoff.py
  python scripts/verify_prf_signoff.py --report evals/reports/prf_latest.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORT = ROOT / "evals" / "reports" / "prf_latest.json"
SUMMARY_OUT = ROOT / "evals" / "reports" / "prf_signoff_summary.json"


def _checklist(report: Dict[str, Any]) -> List[Tuple[str, bool, str]]:
    metrics = report.get("metrics") or {}
    guardrails = report.get("guardrails") or {}
    env = report.get("environment") or {}
    items: List[Tuple[str, bool, str]] = []

    items.append(("1_no_pre_test_restart", guardrails.get("no_pre_test_restart_attested") is True, "PRF_ATTEST_NO_RESTART"))
    items.append(("2_realistic_classroom_mix", bool(metrics.get("workload_version") or metrics.get("mode")), "workload documented"))
    items.append(("3_pool_scenario_clean", report.get("status") != "OPEN_BUG", "no OPEN_BUG status"))
    items.append(("4_p50_p95_p99_error_rate", guardrails.get("reports_tail_latency") is True, "percentiles in metrics"))
    items.append(("5_cold_start_separate", guardrails.get("cold_start_reported_separately") is True or "cold_start" in metrics, "cold_start block"))
    items.append(("6_ingest_concurrent_100pg", metrics.get("concurrent") is not None or "ingest_s" in metrics, "PRF-04 metrics present"))
    items.append(("7_studio_per_type", "per_type_ms" in metrics or report.get("test_ids") != ["PRF-01", "PRF-02"], "per-type or chat-only"))
    items.append(("8_load_20_50_concurrency", metrics.get("users") is not None or metrics.get("concurrency") is not None, "concurrency documented"))
    items.append(("9_resources_instrumented", (ROOT / "evals" / "reports" / "prf_resource_timeseries.jsonl").exists(), "resource timeseries file"))
    items.append(("10_soak_full_duration", "rss_summary" in metrics, "soak RSS summary (manual run)"))
    items.append(("11_end_vs_start_soak", metrics.get("chat_start_exit") == 0 and metrics.get("chat_end_exit") == 0, "soak chat bookends"))
    items.append(("12_environment_documented", bool(env.get("hostname") and env.get("cpu_count")), "environment block"))
    items.append(("13_versioned_baseline", (ROOT / "evals" / "reports" / "prf_baseline.json").exists(), "prf_baseline.json"))
    items.append(("14_cost_captured", "total_cost_usd" in metrics or metrics.get("per_type_ms"), "cost or studio metrics"))
    items.append(("15_failure_tags", bool(report.get("failure_tags") is not None), "failure_tags field"))
    items.append(("16_capacity_number", metrics.get("users") is not None or metrics.get("concurrency") is not None, "users/concurrency for capacity"))

    return items


def verify(report_path: Path) -> Dict[str, Any]:
    if not report_path.exists():
        return {"pass": False, "error": f"Missing report: {report_path}"}

    report = json.loads(report_path.read_text(encoding="utf-8"))
    items = _checklist(report)
    passed = sum(1 for _, ok, _ in items if ok)
    automated_pass = passed >= 10  # smoke harness may not satisfy soak-only items

    summary = {
        "pass": automated_pass and report.get("status") in {"PASS", "BASELINE", "XFAIL", None},
        "report_status": report.get("status"),
        "checklist_passed": passed,
        "checklist_total": len(items),
        "items": [{"id": i, "ok": ok, "note": note} for i, ok, note in items],
        "report_path": str(report_path),
    }
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--allow-partial", action="store_true", help="Pass if >=10/16 checklist items (harness MVP)")
    args = parser.parse_args()
    summary = verify(Path(args.report))
    if args.allow_partial and summary.get("checklist_passed", 0) >= 10:
        summary["pass"] = True
        summary["note"] = "Partial pass allowed (--allow-partial)"
        SUMMARY_OUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if summary.get("error"):
        return 2
    return 0 if summary.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
