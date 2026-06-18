#!/usr/bin/env python3
"""
Master runner for ING + RET production test suite.

Usage:
  python scripts/generate_test_fixtures.py
  INTEGRATION_TESTS=1 python scripts/run_ing_ret_suite.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str]) -> int:
    print(f"\n>>> {' '.join(cmd)}")
    return subprocess.call(cmd, cwd=str(ROOT), env=os.environ.copy())


def main() -> int:
    os.environ.setdefault("INTEGRATION_TESTS", "1")

    steps = [
        [sys.executable, "scripts/generate_test_fixtures.py"],
        [sys.executable, "-m", "pytest", "tests/unit/test_file_validator.py", "tests/unit/test_pdf_upload_validator.py", "-q"],
        [sys.executable, "-m", "pytest", "tests/integration/test_ingestion_suite.py", "-q", "-m", "integration and not slow"],
        [sys.executable, "-m", "pytest", "tests/integration/test_retrieval_suite.py", "-q", "-m", "integration and not slow"],
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
        [sys.executable, "evals/runners/retrieval_eval.py"],
    ]
    for cmd in steps:
        code = run(cmd)
        if code != 0:
            print(f"Step failed with exit code {code}: {cmd}")
            return code
    print("\nING+RET suite completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
