#!/usr/bin/env python3
"""
Orchestrate IPI + CSF production sign-off (MVP matrix).

Usage:
  python scripts/run_ipi_csf_signoff.py
  python scripts/run_ipi_csf_signoff.py --ipi-only
  CSF_PROBES_APPROVED=1 python scripts/run_ipi_csf_signoff.py --csf-only
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "evals" / "reports" / "ipi_csf_signoff_latest.json"
REPORTS = ROOT / "evals" / "reports"
IPI_JUNIT = REPORTS / "ipi_pytest.xml"
IPI_SLOW_JUNIT = REPORTS / "ipi_pytest_slow.xml"
CSF_JUNIT = REPORTS / "csf_pytest.xml"

sys.path.insert(0, str(ROOT))

_gate_path = ROOT / "scripts" / "run_prod_gate.py"
import importlib.util

_spec = importlib.util.spec_from_file_location("run_prod_gate", _gate_path)
_gate = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_gate)
preflight = _gate.preflight
ensure_api_healthy = _gate.ensure_api_healthy
ensure_api_transaction_pooler = _gate.ensure_api_transaction_pooler
run = _gate.run


def _csf_approved() -> bool:
    return os.getenv("CSF_PROBES_APPROVED", "").strip().lower() in {"1", "true", "yes"}


def _step(name: str, cmd: list[str], layers: dict) -> int:
    print(f"\n=== {name} ===")
    code = run(cmd)
    layers[name] = code
    return code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ipi-only", action="store_true")
    parser.add_argument("--csf-only", action="store_true")
    parser.add_argument("--skip-sync", action="store_true")
    args = parser.parse_args()

    base_url = os.getenv("NOTEBOOKLM_API_URL", "http://127.0.0.1:8000")
    os.environ.setdefault("INTEGRATION_TESTS", "1")

    ok, msg = preflight(base_url)
    if not ok:
        print(f"Preflight failed: {msg}")
        return 2
    ensure_api_transaction_pooler(base_url)
    ensure_api_healthy(base_url)

    layers: dict[str, int] = {}
    run_ipi = not args.csf_only
    run_csf = not args.ipi_only

    if run_ipi:
        if _step("generate_ipi_fixtures", [sys.executable, "scripts/generate_ipi_fixtures.py"], layers):
            _write_report(layers, base_url)
            return layers["generate_ipi_fixtures"]
        if _step("log_ipi_ingestion_survival", [sys.executable, "scripts/log_ipi_ingestion_survival.py"], layers):
            _write_report(layers, base_url)
            return layers["log_ipi_ingestion_survival"]
        if _step(
            "unit_source_content_guard",
            [sys.executable, "-m", "pytest", "tests/unit/test_source_content_guard.py", "-q"],
            layers,
        ):
            _write_report(layers, base_url)
            return layers["unit_source_content_guard"]
        REPORTS.mkdir(parents=True, exist_ok=True)
        if _step(
            "ipi_pytest_not_slow",
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/integration/test_ipi_suite.py",
                "-m",
                "integration and ipi and not slow",
                "-v",
                f"--junitxml={IPI_JUNIT}",
            ],
            layers,
        ):
            _write_report(layers, base_url)
            return layers["ipi_pytest_not_slow"]
        _step(
            "ipi_pytest_slow",
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/integration/test_ipi_suite.py",
                "-m",
                "integration and ipi and slow",
                "-v",
                f"--junitxml={IPI_SLOW_JUNIT}",
            ],
            layers,
        )
        _step(
            "verify_ipi_signoff",
            [
                sys.executable,
                "scripts/verify_ipi_signoff.py",
                f"--junit={IPI_JUNIT}",
                f"--slow-junit={IPI_SLOW_JUNIT}",
                "--unit-guard-passed",
            ],
            layers,
        )

    if run_csf:
        if not _csf_approved():
            print(
                "CSF skipped: set CSF_PROBES_APPROVED=1 after reviewing evals/datasets/csf_* "
                "(see csf_probe_review_checklist.md)"
            )
            layers["csf_pytest"] = 0
        else:
            ensure_api_healthy(base_url)
            if _step(
                "csf_pytest",
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "tests/integration/test_csf_suite.py",
                    "-m",
                    "integration and child_safety and not slow",
                    "-v",
                    f"--junitxml={CSF_JUNIT}",
                ],
                layers,
            ):
                _write_report(layers, base_url)
                return layers["csf_pytest"]
            _step(
                "export_csf_human_review_batch",
                [sys.executable, "scripts/export_csf_human_review_batch.py"],
                layers,
            )
            csf_verify_cmd = [sys.executable, "scripts/verify_csf_signoff.py", f"--junit={CSF_JUNIT}"]
            approved = ROOT / "evals" / "reports" / "csf_human_review_approved.json"
            if approved.exists():
                csf_verify_cmd.append("--human-approved")
            _step("verify_csf_signoff", csf_verify_cmd, layers)

    if not args.skip_sync:
        _step("sync_bucket_results", [sys.executable, "scripts/sync_bucket_results_from_pytest.py"], layers)
        _step(
            "generate_spreadsheet",
            [sys.executable, "docs/Test_Bucket_Results/generate_test_results_spreadsheet.py"],
            layers,
        )

    _write_report(layers, base_url)
    failed = [k for k, v in layers.items() if v != 0 and k not in ("verify_ipi_signoff", "verify_csf_signoff")]
    if failed:
        print(f"Sign-off completed with failures: {failed}")
        return 1
    return 0


def _write_report(layers: dict[str, int], base_url: str) -> None:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "csf_probes_approved": _csf_approved(),
        "layers": layers,
        "artifacts": {
            "ipi_survival": str(REPORTS / "ipi_ingestion_survival.json"),
            "ipi_junit": str(IPI_JUNIT),
            "ipi_slow_junit": str(IPI_SLOW_JUNIT),
            "csf_junit": str(CSF_JUNIT),
        },
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {REPORT}")


if __name__ == "__main__":
    raise SystemExit(main())
