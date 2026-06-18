#!/usr/bin/env python3
"""Sync IPI/CSF spreadsheet overrides from pytest JUnit reports and survival log."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts._pytest_junit_helpers import (  # noqa: E402
    csf_row_results,
    ipi_row_results,
    parse_junit,
)

OUT = ROOT / "evals" / "reports" / "bucket_result_overrides.json"
IPI_JUNIT = ROOT / "evals" / "reports" / "ipi_pytest.xml"
IPI_SLOW = ROOT / "evals" / "reports" / "ipi_pytest_slow.xml"
CSF_JUNIT = ROOT / "evals" / "reports" / "csf_pytest.xml"


def _count_rows(rows: dict[str, dict]) -> dict[str, int]:
    counts = {"PASS": 0, "XFAIL": 0, "FAIL": 0, "SKIP": 0, "PENDING": 0, "PARTIAL": 0}
    for data in rows.values():
        r = str(data.get("result", "PENDING")).upper()
        counts[r] = counts.get(r, 0) + 1
    return counts


def main() -> int:
    ipi_outcomes = parse_junit(IPI_JUNIT)
    ipi_slow = parse_junit(IPI_SLOW)
    csf_outcomes = parse_junit(CSF_JUNIT)

    rows: dict[str, dict] = {}

    for test_id, data in ipi_row_results(ipi_outcomes, ipi_slow).items():
        rows[f"Indirect Injection|{test_id}"] = data

    for test_id, data in csf_row_results(csf_outcomes).items():
        rows[f"Child Safety|{test_id}"] = data

    rows["Child Safety|CSF-04"] = {
        "result": "SKIP",
        "description": "Export-only; curriculum + safety reviewer sign-off linked to GRD refusal templates.",
        "issues": "",
    }
    rows["Child Safety|CSAM (policy)"] = {
        "result": "SKIP",
        "description": "No developer-authored prompts. OpenAI moderation child-safety docs + chat_policy.default.yaml review.",
        "issues": "Documented in CSF_TEST_SUITE.md.",
    }

    ipi_counts = _count_rows({k: v for k, v in rows.items() if k.startswith("Indirect Injection")})
    csf_counts = _count_rows({k: v for k, v in rows.items() if k.startswith("Child Safety")})

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rows": rows,
        "summary": {
            "Indirect Injection": {
                "total": 6,
                **{k.lower(): v for k, v in ipi_counts.items()},
                "action": "MVP IPI sign-off from live integration runs",
            },
            "Child Safety": {
                "total": 7,
                **{k.lower(): v for k, v in csf_counts.items()},
                "action": "CSF-04 + CSAM SKIP; probes approved + human review JSON",
            },
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} ({len(rows)} row overrides)")
    pending = [k for k, v in rows.items() if v.get("result") == "PENDING"]
    if pending:
        print(f"Still PENDING: {pending}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
