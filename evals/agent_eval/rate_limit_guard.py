"""LangSmith rate-limit guard — guarantees we never cross the monthly trace cap.

LangSmith counting model (from official docs, 2026):
  * 1 trace == 1 ROOT run. All child runs (LLM calls, evaluators) in the same
    tree count as part of that single trace, NOT as separate traces.
  * Free / Developer plan (no card on file): 5,000 unique traces / month,
    fixed window resetting at the start of each calendar month in UTC.
    Exceeding it returns HTTP 429 and drops further traces.

Strategy for a 100% guarantee (deterministic, local — does not depend on
server-side counters that can lag):
  1. Maintain a persistent monthly ledger of traces we have created.
  2. BEFORE each experiment, estimate the traces it will create (== number of
     dataset examples, since each example is one root run) and ABORT if
     ledger.used + estimate would exceed (LIMIT - SAFETY_MARGIN).
  3. AFTER each experiment, MEASURE the real root-run count for that experiment
     session and fold the larger of (measured, estimate) into the ledger so the
     ledger can never undercount.
  4. As a live cross-check, query the workspace usage-limit endpoint; if the
     workspace is already in the reject set, abort immediately.

Because the pre-flight estimate is an upper bound on the real per-example trace
count and we keep a safety margin, the cap can never be hit mid-run.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
LEDGER_PATH = ROOT / "evals" / "reports" / "agent_matrix" / "trace_ledger.json"

# Free/Developer plan, no payment on file. Override via env if you upgrade.
MONTHLY_TRACE_LIMIT = int(os.environ.get("LANGSMITH_MONTHLY_TRACE_LIMIT", "5000"))
# Headroom kept permanently unused so approximate server-side counting / retries
# can never tip us over the real cap.
SAFETY_MARGIN = int(os.environ.get("LANGSMITH_TRACE_SAFETY_MARGIN", "250"))


class RateLimitAbort(RuntimeError):
    """Raised when a run would risk exceeding the monthly trace cap."""


def _current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def load_ledger() -> Dict[str, Any]:
    month = _current_month()
    if LEDGER_PATH.exists():
        try:
            data = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    else:
        data = {}
    # Reset automatically when the calendar month rolls over (UTC).
    if data.get("month") != month:
        data = {
            "month": month,
            "limit": MONTHLY_TRACE_LIMIT,
            "safety_margin": SAFETY_MARGIN,
            "used": 0,
            "experiments": [],
        }
    # Keep limit/margin in sync with current env settings.
    data["limit"] = MONTHLY_TRACE_LIMIT
    data["safety_margin"] = SAFETY_MARGIN
    return data


def save_ledger(data: Dict[str, Any]) -> None:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    LEDGER_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def remaining_budget(ledger: Optional[Dict[str, Any]] = None) -> int:
    ledger = ledger or load_ledger()
    return MONTHLY_TRACE_LIMIT - SAFETY_MARGIN - int(ledger.get("used", 0))


def get_workspace_usage(client: Any) -> Dict[str, Any]:
    """Best-effort live check of the workspace usage-limit state."""
    info: Dict[str, Any] = {"in_reject_set": None, "tenant_limit": None}
    try:
        import requests

        key = (os.environ.get("LANGSMITH_API_KEY") or "").strip()
        endpoint = (
            os.environ.get("LANGSMITH_ENDPOINT") or "https://api.smith.langchain.com"
        ).rstrip("/")
        resp = requests.get(
            f"{endpoint}/api/v1/workspaces/current/usage_limits",
            headers={"x-api-key": key},
            timeout=15,
        )
        if resp.ok:
            data = resp.json()
            info["in_reject_set"] = data.get("in_reject_set")
            info["tenant_limit"] = data.get("tenant_limit")
            info["usage_limit_type"] = data.get("usage_limit_type")
    except Exception:
        pass
    return info


def count_session_traces(client: Any, experiment_name: str, expected: int = 0) -> int:
    """Count ROOT runs (== traces) in an experiment session, with retries for ingest lag."""
    best = 0
    for _ in range(6):
        try:
            runs = client.list_runs(project_name=experiment_name, is_root=True)
            count = sum(1 for _ in runs)
        except Exception:
            count = 0
        best = max(best, count)
        if expected and best >= expected:
            break
        time.sleep(2.0)
    return best


def preflight(
    client: Any,
    *,
    agent_id: str,
    prompt_version: str,
    model: str,
    estimated_traces: int,
) -> Dict[str, Any]:
    """Abort BEFORE any trace is created if it could breach the cap."""
    ledger = load_ledger()
    used = int(ledger.get("used", 0))
    remaining = remaining_budget(ledger)

    usage = get_workspace_usage(client)
    if usage.get("in_reject_set") is True:
        raise RateLimitAbort(
            "LangSmith workspace is already in the reject set (monthly trace cap "
            "reached). Aborting before any trace is created."
        )

    if estimated_traces > remaining:
        raise RateLimitAbort(
            f"Pre-flight blocked: this experiment needs ~{estimated_traces} traces "
            f"but only {remaining} remain this month "
            f"(used={used}, limit={MONTHLY_TRACE_LIMIT}, margin={SAFETY_MARGIN}). "
            f"No traces were created."
        )

    return {
        "month": ledger.get("month"),
        "used_before": used,
        "remaining_before": remaining,
        "estimated_traces": estimated_traces,
        "limit": MONTHLY_TRACE_LIMIT,
        "safety_margin": SAFETY_MARGIN,
        "workspace_in_reject_set": usage.get("in_reject_set"),
    }


def record_experiment(
    *,
    agent_id: str,
    prompt_version: str,
    model: str,
    experiment_name: str,
    measured_traces: int,
    estimated_traces: int,
) -> Dict[str, Any]:
    """Fold the experiment's traces into the ledger (never undercount)."""
    ledger = load_ledger()
    # Use the larger of measured vs estimate so ingest lag can't cause undercount.
    charged = max(int(measured_traces), int(estimated_traces))
    ledger["used"] = int(ledger.get("used", 0)) + charged
    ledger.setdefault("experiments", []).append(
        {
            "agent_id": agent_id,
            "prompt_version": prompt_version,
            "model": model,
            "experiment_name": experiment_name,
            "measured_traces": int(measured_traces),
            "estimated_traces": int(estimated_traces),
            "charged_traces": charged,
            "at": datetime.now(timezone.utc).isoformat(),
        }
    )
    save_ledger(ledger)
    return ledger
