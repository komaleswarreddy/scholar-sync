#!/usr/bin/env python3
"""
Run full PRF validation suite and merge reports.

Usage:
  PRF_ATTEST_NO_RESTART=1 python scripts/run_prf_all.py
  PRF_ATTEST_NO_RESTART=1 python scripts/run_prf_all.py --quick   # smoke only
  PRF_ATTEST_NO_RESTART=1 python scripts/run_prf_all.py --with-load --with-soak
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "evals" / "reports"
PY = sys.executable


def _run(cmd: List[str], *, env: dict | None = None) -> tuple[int, str]:
    merged = os.environ.copy()
    merged.setdefault("PRF_ATTEST_NO_RESTART", "1")
    merged.setdefault("PYTHONIOENCODING", "utf-8")
    if env:
        merged.update(env)
    print(f"\n>>> {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=str(ROOT), env=merged, capture_output=True, text=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    if out.strip():
        print(out[-4000:] if len(out) > 4000 else out)
    return proc.returncode, out


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _merge_reports(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    test_ids: List[str] = []
    metrics: Dict[str, Any] = {}
    failure_tags: List[str] = []
    statuses: List[str] = []
    for r in results:
        if not r:
            continue
        test_ids.extend(r.get("test_ids") or [])
        metrics.update(r.get("metrics") or {})
        failure_tags.extend(r.get("failure_tags") or [])
        statuses.append(r.get("status", "unknown"))

    if "OPEN_BUG" in failure_tags or "open_bug" in failure_tags:
        overall = "OPEN_BUG"
    elif any(s == "FAIL" for s in statuses):
        overall = "FAIL"
    elif all(s in {"PASS", "BASELINE", "XFAIL"} for s in statuses if s):
        overall = "PASS" if all(s in {"PASS", "BASELINE"} for s in statuses if s) else "XFAIL"
    else:
        overall = statuses[-1] if statuses else "unknown"

    from tests.helpers.performance_stats import build_prf_report, collect_environment, write_prf_report

    report = build_prf_report(
        test_ids=sorted(set(test_ids)),
        status=overall,
        metrics=metrics,
        environment=collect_environment(),
        failure_tags=sorted(set(failure_tags)),
        notes="Merged by run_prf_all.py",
    )
    write_prf_report(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="Smoke runners only")
    parser.add_argument("--with-load", action="store_true", help="Include PRF-06 load (smoke or full)")
    parser.add_argument("--with-soak", action="store_true", help="Include PRF-07 soak (default 30m)")
    parser.add_argument("--load-full", action="store_true", help="15m/50 users load instead of smoke")
    parser.add_argument("--chat-n", type=int, default=0, help="Override chat request count for full mode")
    parser.add_argument("--base-url", default=os.getenv("NOTEBOOKLM_API_URL", "http://127.0.0.1:8000"))
    args = parser.parse_args()

    os.environ.setdefault("PRF_ATTEST_NO_RESTART", "1")
    quick = args.quick
    reports: List[Dict[str, Any]] = []
    exit_codes: Dict[str, int] = {}

    chat_cmd = [PY, "scripts/run_prf_chat_latency.py", "--smoke" if quick else "--full", "--record-baseline"]
    if args.chat_n:
        chat_cmd.extend(["--n", str(args.chat_n)])
    code, _ = _run(chat_cmd + ["--base-url", args.base_url])
    exit_codes["chat"] = code
    reports.append(_load_json(REPORTS / "prf_chat_latency.json"))

    for name, script, extra, report_name in [
        ("scoped", "run_prf_scoped_retrieval.py", ["--smoke" if quick else "--full"], "prf_scoped_retrieval.json"),
        ("ingest", "run_prf_ingestion.py", ["--smoke" if quick else "--full"] + ([] if quick else ["--concurrent"]), "prf_ingestion.json"),
        ("studio", "run_prf_studio_latency.py", ["--smoke" if quick else "--full"], "prf_studio_latency.json"),
    ]:
        code, _ = _run([PY, f"scripts/{script}"] + extra + ["--base-url", args.base_url])
        exit_codes[name] = code
        reports.append(_load_json(REPORTS / report_name))

    if args.with_load or not quick:
        load_args = ["--smoke"] if quick and not args.load_full else (["--full"] if args.load_full else ["--smoke"])
        code, _ = _run([PY, "scripts/run_prf_load.py"] + load_args + ["--base-url", args.base_url])
        exit_codes["load"] = code
        reports.append(_load_json(REPORTS / "prf_load.json"))

    if args.with_soak:
        soak_dur = os.getenv("PRF_SOAK_DURATION", "30m")
        code, _ = _run(
            [PY, "scripts/run_prf_soak.py", "--duration", soak_dur, "--base-url", args.base_url],
            env={"PRF_SOAK_DURATION": soak_dur},
        )
        exit_codes["soak"] = code
        reports.append(_load_json(REPORTS / "prf_soak.json"))

    merged = _merge_reports(reports)
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "exit_codes": exit_codes,
        "merged_status": merged.get("status"),
        "quick": quick,
    }
    (REPORTS / "prf_all_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))

    code, _ = _run([PY, "scripts/verify_prf_signoff.py", "--allow-partial"])
    exit_codes["signoff"] = code

    if merged.get("status") == "OPEN_BUG":
        return 1
    if any(v not in (0, None) for k, v in exit_codes.items() if k != "signoff"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
