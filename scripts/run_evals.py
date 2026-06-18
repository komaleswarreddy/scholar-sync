#!/usr/bin/env python3
"""Run evaluation suite entrypoint."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description="ScholarSync eval suite")
    parser.add_argument("--agent", default="intent_classifier")
    parser.add_argument("--e2e", action="store_true")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    if args.e2e:
        cmd = [sys.executable, str(ROOT / "eval_e2e.py"), "--limit", str(args.limit)]
    else:
        cmd = [
            sys.executable,
            str(ROOT / "eval.py"),
            "--agent",
            args.agent,
            "--limit",
            str(args.limit),
        ]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
