#!/usr/bin/env python3
"""
Problem Solver verification gate — unit + optional live API checks.

Usage:
  python scripts/verify_problem_solver_e2e.py
  python scripts/verify_problem_solver_e2e.py --live   # requires API + auth env
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "evals" / "reports" / "problem_solver_verify.json"

UNIT_TESTS = [
    "tests/unit/test_problem_solver.py",
    "tests/unit/test_problem_solver_transitions.py",
    "tests/unit/test_problem_subject_inference.py",
    "tests/unit/test_problem_solver_checkpoint.py",
    "tests/unit/test_markdown_math_preprocess.py",
]

QUESTION_EXTRACTION_TESTS = [
    "tests/unit/test_source_question_extraction.py",
    "tests/unit/test_question_regex_parser.py",
]


def run_pytest(paths: list[str]) -> tuple[int, str]:
    cmd = [sys.executable, "-m", "pytest", *paths, "-q", "--tb=short"]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def check_feature_flag() -> dict:
    env_path = ROOT / ".env"
    enabled = os.getenv("ENABLE_PROBLEM_SOLVER", "").lower() in ("1", "true", "yes")
    if env_path.exists() and not enabled:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("ENABLE_PROBLEM_SOLVER="):
                enabled = line.split("=", 1)[1].strip().lower() in ("1", "true", "yes")
                break
    web_env = ROOT / "apps" / "web" / ".env.local"
    web_enabled = False
    if web_env.exists():
        for line in web_env.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("NEXT_PUBLIC_ENABLE_PROBLEM_SOLVER="):
                web_enabled = line.split("=", 1)[1].strip().lower() in ("1", "true", "yes")
    return {
        "backend_flag": enabled,
        "frontend_flag": web_enabled,
        "env_file_exists": env_path.exists(),
    }


def check_openapi_routes() -> dict:
    try:
        import urllib.request

        url = os.getenv("API_BASE_URL", "http://127.0.0.1:8000") + "/openapi.json"
        with urllib.request.urlopen(url, timeout=10) as resp:
            spec = json.loads(resp.read().decode("utf-8"))
        paths = spec.get("paths", {})
        ps_paths = [p for p in paths if "/problem-solver" in p]
        return {"ok": len(ps_paths) > 0, "route_count": len(ps_paths), "sample": ps_paths[:5]}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Problem Solver implementation")
    parser.add_argument("--live", action="store_true", help="Also check OpenAPI routes on running API")
    parser.add_argument(
        "--questions",
        action="store_true",
        help="Also run source question extraction unit tests",
    )
    args = parser.parse_args()

    test_paths = list(UNIT_TESTS)
    if args.questions:
        test_paths.extend(QUESTION_EXTRACTION_TESTS)

    results: dict = {"steps": []}

    flags = check_feature_flag()
    results["flags"] = flags
    results["steps"].append({"name": "feature_flags", "pass": flags["backend_flag"] and flags["frontend_flag"]})

    code, output = run_pytest(test_paths)
    results["steps"].append({"name": "unit_tests", "pass": code == 0, "exit_code": code})
    results["pytest_output"] = output[-4000:]

    if args.live:
        api = check_openapi_routes()
        results["steps"].append({"name": "openapi_problem_solver_routes", "pass": api.get("ok", False), **api})

    results["pass"] = all(step.get("pass") for step in results["steps"])
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print(json.dumps(results, indent=2))
    if not results["pass"]:
        print("\nFAILED — see evals/reports/problem_solver_verify.json", file=sys.stderr)
        return 1
    print("\nPASSED — Problem Solver verification complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
