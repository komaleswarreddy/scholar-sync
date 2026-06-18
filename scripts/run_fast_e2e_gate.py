#!/usr/bin/env python3
"""
Fast accurate ING/RET end-to-end gate (~15–30 min, not hours).

Skips: RET-04 rubric export (slow LLM), TestSprite (run separately when API idle).

Usage:
  INTEGRATION_TESTS=1 python scripts/run_fast_e2e_gate.py
  GATE_CLASSROOM_SHORT=1  # default: 3m / 12 users (set 0 for full 10m / 40 users)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "evals" / "reports" / "fast_e2e_summary.json"

sys.path.insert(0, str(ROOT))
import importlib.util

_gate_path = ROOT / "scripts" / "run_prod_gate.py"
_spec = importlib.util.spec_from_file_location("run_prod_gate", _gate_path)
_gate = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_gate)
preflight = _gate.preflight
ensure_api_healthy = _gate.ensure_api_healthy
ensure_api_transaction_pooler = _gate.ensure_api_transaction_pooler
run = _gate.run
seed_classroom_chat_source = _gate.seed_classroom_chat_source
validate_classroom_locust_result = _gate.validate_classroom_locust_result


def _retrieval_eval_already_passing() -> bool:
    path = ROOT / "evals" / "reports" / "retrieval_latest.json"
    if not path.exists():
        return False
    data = json.loads(path.read_text(encoding="utf-8"))
    passes = data.get("pass") or {}
    return bool(passes) and all(bool(v) for v in passes.values())


def _run_ing_ret_pytest_layers() -> int:
    steps = [
        [sys.executable, "scripts/generate_test_fixtures.py"],
        [sys.executable, "-m", "pytest", "tests/unit/test_file_validator.py", "tests/unit/test_pdf_upload_validator.py", "-q"],
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/integration/test_ingestion_suite.py",
            "-q",
            "-m",
            "integration and not slow",
        ],
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/integration/test_retrieval_suite.py",
            "-q",
            "-m",
            "integration and not slow",
        ],
        [sys.executable, "-m", "pytest", "tests/unit/test_notebook_mode_config.py", "-q"],
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/integration/test_notebook_mode_suite.py",
            "-q",
            "-m",
            "integration and notebook_mode and not slow",
        ],
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit/test_studio_output_validators.py",
            "tests/unit/test_studio_request_schema.py",
            "-q",
        ],
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/integration/test_studio_suite.py",
            "-q",
            "-m",
            "integration and studio and not slow",
        ],
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit/test_academic_integrity.py",
            "tests/unit/test_pii_detector_indian.py",
            "tests/unit/test_rate_limiter_shared.py",
            "tests/unit/test_prompt_injection_protection.py",
            "-q",
        ],
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/integration/test_guardrails_suite.py",
            "-q",
            "-m",
            "integration and guardrails and not slow",
        ],
        [
            sys.executable,
            "scripts/generate_ipi_fixtures.py",
        ],
        [
            sys.executable,
            "scripts/log_ipi_ingestion_survival.py",
        ],
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit/test_source_content_guard.py",
            "-q",
        ],
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/integration/test_ipi_suite.py",
            "-q",
            "-m",
            "integration and ipi and not slow",
        ],
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/integration/test_csf_suite.py",
            "-q",
            "-m",
            "integration and child_safety and not slow",
        ],
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/integration/test_performance_suite.py",
            "-q",
            "-m",
            "integration and performance and not slow",
        ],
    ]
    for cmd in steps:
        code = run(cmd)
        if code != 0:
            return code
    return 0


def main() -> int:
    base_url = os.getenv("NOTEBOOKLM_API_URL", "http://127.0.0.1:8000")
    os.environ.setdefault("INTEGRATION_TESTS", "1")
    os.environ.setdefault("GATE_CLASSROOM_SHORT", "1")

    ok, msg = preflight(base_url)
    if not ok:
        print(f"Preflight failed: {msg}")
        return 2

    ensure_api_transaction_pooler(base_url)
    ensure_api_healthy(base_url)

    layers: dict[str, int] = {}
    force_eval = os.getenv("FAST_FORCE_RETRIEVAL_EVAL", "").strip() in {"1", "true", "yes"}
    skip_eval = not force_eval and _retrieval_eval_already_passing()

    layers["ing_ret_pytest"] = _run_ing_ret_pytest_layers()
    if layers["ing_ret_pytest"] != 0:
        _write_report(layers, base_url)
        return layers["ing_ret_pytest"]

    if skip_eval:
        print("Skipping retrieval_eval (evals/reports/retrieval_latest.json already passing). Set FAST_FORCE_RETRIEVAL_EVAL=1 to re-run.")
        layers["retrieval_eval"] = 0
    else:
        layers["retrieval_eval"] = run(
            [
                sys.executable,
                "evals/runners/retrieval_eval.py",
                "--report",
                "evals/reports/retrieval_latest.json",
            ]
        )
        if layers["retrieval_eval"] != 0:
            _write_report(layers, base_url)
            return layers["retrieval_eval"]

    layers["intent_gate_unit"] = run(
        [sys.executable, "-m", "pytest", "tests/unit/test_intent_gate_academic.py", "-q"]
    )
    if layers["intent_gate_unit"] != 0:
        _write_report(layers, base_url)
        return layers["intent_gate_unit"]

    ensure_api_healthy(base_url)
    try:
        chat_user, chat_source_id = seed_classroom_chat_source(base_url)
    except Exception as exc:  # noqa: BLE001
        print(f"Classroom seed failed: {exc}")
        layers["classroom_locust"] = 1
        _write_report(layers, base_url, error=str(exc))
        return 1

    short = os.getenv("GATE_CLASSROOM_SHORT", "1").strip() in {"1", "true", "yes"}
    stats = ROOT / "evals" / "reports" / "fast_classroom_stats"
    locust_cmd = [
        sys.executable,
        "-m",
        "locust",
        "-f",
        "tests/load/locustfile_classroom.py",
        "--headless",
        "--users",
        "12" if short else "40",
        "--spawn-rate",
        "3" if short else "5",
        "--run-time",
        "3m" if short else "10m",
        "--csv",
        str(stats),
        "--host",
        base_url,
    ]
    layers["classroom_locust"] = validate_classroom_locust_result(
        run(
            locust_cmd,
            env={
                "CLASSROOM_CHAT_USER": chat_user,
                "CLASSROOM_CHAT_SOURCE_ID": chat_source_id,
                "PRF_WORKLOAD": "1",
                "PRF_WORKLOAD_VERSION": "prf_classroom_v1",
            },
        )
    )

    _write_report(layers, base_url)
    failed = [k for k, v in layers.items() if v != 0]
    if failed:
        print(f"Fast E2E failed layers: {failed}")
        return 1
    print("Fast E2E gate: PASS")
    return 0


def _write_report(layers: dict[str, int], base_url: str, error: str | None = None) -> None:
    retrieval_path = ROOT / "evals" / "reports" / "retrieval_latest.json"
    retrieval_pass = {}
    if retrieval_path.exists():
        retrieval_pass = json.loads(retrieval_path.read_text(encoding="utf-8")).get("pass") or {}
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "layers": layers,
        "classroom_mode": "short" if os.getenv("GATE_CLASSROOM_SHORT", "1") in {"1", "true", "yes"} else "full",
        "retrieval_eval_skipped": layers.get("retrieval_eval") == 0 and "retrieval_eval" in layers,
        "retrieval_eval_pass": retrieval_pass,
        "error": error,
        "all_pass": all(v == 0 for v in layers.values()),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Summary: {REPORT}")


if __name__ == "__main__":
    raise SystemExit(main())
