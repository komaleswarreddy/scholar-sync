#!/usr/bin/env python3
"""
Run inlined TestSprite ING/RET scripts locally and report pass count.

Usage:
  INTEGRATION_TESTS=1 python scripts/run_testsprite_local.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TS = ROOT / "testsprite_tests"
PASS_BAR = 18
TOTAL = 23  # TC001 + ING-01..11 + RET-01..11


def main() -> int:
    tc = sorted(TS.glob("TC*.py"))
    scripts = tc + sorted(TS.glob("ING-*.py")) + sorted(TS.glob("RET-*.py"))
    if len(scripts) != TOTAL:
        print(f"Expected {TOTAL} scripts, found {len(scripts)}")
    passed = 0
    failed: list[str] = []
    for path in scripts:
        proc = subprocess.run(
            [sys.executable, str(path)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            passed += 1
            print(f"PASS {path.name}")
        else:
            failed.append(path.name)
            err = (proc.stderr or proc.stdout or "").strip().splitlines()
            tail = err[-1] if err else f"exit {proc.returncode}"
            print(f"FAIL {path.name}: {tail}")
    print(f"\nTestSprite local: {passed}/{len(scripts)} passed (target >= {PASS_BAR})")
    out = ROOT / "evals" / "reports" / "testsprite_local_summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    import json

    out.write_text(
        json.dumps(
            {"passed": passed, "total": len(scripts), "pass_bar": PASS_BAR, "failed": failed},
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0 if passed >= PASS_BAR else 1


if __name__ == "__main__":
    raise SystemExit(main())
