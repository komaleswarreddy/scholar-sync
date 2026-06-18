"""Performance statistics, baselines, and PRF report builders."""

from __future__ import annotations

import json
import os
import platform
import socket
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = ROOT / "evals" / "reports"
BASELINE_PATH = REPORTS_DIR / "prf_baseline.json"
LATEST_PATH = REPORTS_DIR / "prf_latest.json"

POOL_EXHAUSTION_MARKERS = (
    "EMAXCONNSESSION",
    "MaxClientsInSessionMode",
    "max clients reached",
    "max_clients",
)


class FailureTag(str, Enum):
    LATENCY = "latency"
    ERROR_SPIKE = "error_spike"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    HARNESS_ARTIFACT = "harness_artifact"
    OPEN_BUG = "open_bug"


def percentiles(values: List[float]) -> Dict[str, float]:
    """Compute P50/P95/P99 from a list of numeric samples."""
    if not values:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "n": 0}
    sorted_vals = sorted(values)
    n = len(sorted_vals)

    def _pct(p: float) -> float:
        if n == 1:
            return float(sorted_vals[0])
        idx = min(n - 1, max(0, int(round(p * (n - 1)))))
        return float(sorted_vals[idx])

    return {
        "p50": _pct(0.50),
        "p95": _pct(0.95),
        "p99": _pct(0.99),
        "n": n,
        "mean": sum(sorted_vals) / n,
    }


def error_rate(errors: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return errors / total


def detect_pool_exhaustion(text: str) -> bool:
    lower = (text or "").lower()
    return any(m.lower() in lower for m in POOL_EXHAUSTION_MARKERS)


def collect_environment() -> Dict[str, Any]:
    """Document test environment for capacity planning."""
    db_url = os.getenv("DATABASE_URL", "")
    db_host = ""
    if db_url:
        try:
            parsed = urlparse(db_url)
            db_host = parsed.hostname or "unknown"
        except Exception:  # noqa: BLE001
            db_host = "redacted"
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "python_version": platform.python_version(),
        "base_url": os.getenv("NOTEBOOKLM_API_URL", "http://127.0.0.1:8000"),
        "database_host": db_host,
        "gate_classroom_short": os.getenv("GATE_CLASSROOM_SHORT", ""),
        "prf_attest_no_restart": os.getenv("PRF_ATTEST_NO_RESTART", ""),
        "notes": os.getenv("PRF_ENV_NOTES", ""),
    }


def require_no_restart_attestation() -> None:
    """Guardrail: refuse PRF runs without explicit no-restart attestation."""
    if os.getenv("PRF_ATTEST_NO_RESTART", "").strip() not in {"1", "true", "yes"}:
        raise RuntimeError(
            "PRF guardrail: set PRF_ATTEST_NO_RESTART=1 to attest the API was not "
            "restarted immediately before this run."
        )


def compare_baseline(
    current: Dict[str, Any],
    baseline: Dict[str, Any],
    *,
    regression_pct: float = 10.0,
) -> List[str]:
    """Return list of regression warnings (>regression_pct on latency or cost)."""
    warnings: List[str] = []
    for key in ("ttft_ms", "e2e_ms", "p95_ms", "cost_usd"):
        cur = current.get(key)
        base = baseline.get(key)
        if cur is None or base is None:
            continue
        try:
            cur_f = float(cur)
            base_f = float(base)
        except (TypeError, ValueError):
            continue
        if base_f <= 0:
            continue
        pct_change = ((cur_f - base_f) / base_f) * 100.0
        if pct_change > regression_pct:
            warnings.append(f"{key} regressed {pct_change:.1f}% vs baseline ({cur_f} vs {base_f})")
    return warnings


def build_prf_report(
    *,
    test_ids: List[str],
    status: str,
    metrics: Dict[str, Any],
    environment: Optional[Dict[str, Any]] = None,
    failure_tags: Optional[List[str]] = None,
    notes: str = "",
    duration_s: Optional[float] = None,
    sample_size: int = 0,
) -> Dict[str, Any]:
    """Standard PRF report schema."""
    env = environment or collect_environment()
    report: Dict[str, Any] = {
        "schema": "prf_report_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "test_ids": test_ids,
        "status": status,
        "metrics": metrics,
        "environment": env,
        "failure_tags": list(failure_tags or []),
        "notes": notes,
        "duration_s": duration_s,
        "sample_size": sample_size,
        "guardrails": {
            "no_pre_test_restart_attested": env.get("prf_attest_no_restart") in {"1", "true", "yes"},
            "reports_tail_latency": bool(metrics.get("percentiles")),
            "cold_start_reported_separately": "cold_start" in metrics,
        },
    }
    return report


def write_prf_report(report: Dict[str, Any], path: Optional[Path] = None) -> Path:
    out = path or LATEST_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return out


def load_baseline() -> Dict[str, Any]:
    if not BASELINE_PATH.exists():
        return {}
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def update_baseline(report: Dict[str, Any]) -> None:
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")


def merge_into_latest(partial: Dict[str, Any]) -> Dict[str, Any]:
    """Merge partial metrics into prf_latest.json."""
    existing: Dict[str, Any] = {}
    if LATEST_PATH.exists():
        try:
            existing = json.loads(LATEST_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
    merged_metrics = {**(existing.get("metrics") or {}), **(partial.get("metrics") or partial)}
    test_ids = list(set((existing.get("test_ids") or []) + (partial.get("test_ids") or [])))
    report = build_prf_report(
        test_ids=test_ids,
        status=partial.get("status", existing.get("status", "unknown")),
        metrics=merged_metrics,
        environment=partial.get("environment") or existing.get("environment"),
        failure_tags=list(set((existing.get("failure_tags") or []) + (partial.get("failure_tags") or []))),
        notes=partial.get("notes", existing.get("notes", "")),
        duration_s=partial.get("duration_s", existing.get("duration_s")),
        sample_size=partial.get("sample_size", existing.get("sample_size", 0)),
    )
    write_prf_report(report)
    return report
