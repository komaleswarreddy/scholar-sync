#!/usr/bin/env python3
"""
Sidecar resource sampler for PRF-06/07 load and soak runs.

Polls API process RSS every N seconds; appends JSONL timeseries.

Usage:
  python scripts/prf_resource_sampler.py --duration 7200 --interval 30
  python scripts/prf_resource_sampler.py --pid 12345 --out evals/reports/prf_resource_timeseries.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "evals" / "reports" / "prf_resource_timeseries.jsonl"


def _find_api_pid(port: int = 8000) -> int | None:
    if sys.platform == "win32":
        ps = (
            f"(Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
            "Select-Object -ExpandProperty OwningProcess -Unique | Select-Object -First 1)"
        )
        try:
            out = subprocess.check_output(["powershell", "-NoProfile", "-Command", ps], text=True).strip()
            return int(out) if out.isdigit() else None
        except Exception:  # noqa: BLE001
            return None
    try:
        out = subprocess.check_output(["bash", "-lc", f"lsof -ti :{port}"], text=True).strip()
        return int(out.split()[0]) if out else None
    except Exception:  # noqa: BLE001
        return None


def _rss_mb(pid: int) -> float | None:
    try:
        import psutil  # type: ignore

        proc = psutil.Process(pid)
        return proc.memory_info().rss / (1024 * 1024)
    except ImportError:
        return None
    except Exception:  # noqa: BLE001
        return None


def sample_loop(*, pid: int | None, duration_s: float, interval_s: float, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + duration_s
    samples: list[dict] = []
    start_rss: float | None = None

    while time.time() < deadline:
        ts = datetime.now(timezone.utc).isoformat()
        rss = _rss_mb(pid) if pid else None
        if rss is not None and start_rss is None:
            start_rss = rss
        row = {
            "timestamp_utc": ts,
            "pid": pid,
            "rss_mb": rss,
            "notes": "psutil unavailable" if rss is None and pid else "",
        }
        samples.append(row)
        with out_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        time.sleep(interval_s)

    if start_rss and samples:
        end_rss = samples[-1].get("rss_mb")
        if end_rss:
            growth_pct = ((end_rss - start_rss) / start_rss) * 100.0 if start_rss > 0 else 0.0
            summary_path = out_path.with_suffix(".summary.json")
            summary_path.write_text(
                json.dumps(
                    {
                        "start_rss_mb": start_rss,
                        "end_rss_mb": end_rss,
                        "growth_pct": growth_pct,
                        "sample_count": len(samples),
                        "duration_s": duration_s,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            print(f"RSS growth: {growth_pct:.1f}% ({start_rss:.1f} -> {end_rss:.1f} MB)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=7200.0, help="Sample duration seconds")
    parser.add_argument("--interval", type=float, default=30.0, help="Sample interval seconds")
    parser.add_argument("--pid", type=int, default=0, help="API process PID (auto-detect if 0)")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    pid = args.pid or _find_api_pid(args.port)
    if not pid:
        print("Warning: could not detect API PID; sampling will record timestamps only")
    else:
        print(f"Sampling PID {pid} every {args.interval}s for {args.duration}s")

    sample_loop(pid=pid, duration_s=args.duration, interval_s=args.interval, out_path=Path(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
