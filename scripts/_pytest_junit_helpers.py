"""Parse pytest JUnit XML reports for IPI/CSF sign-off and spreadsheet sync."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def _case_outcome(case: ET.Element) -> str:
    if case.find("skipped") is not None:
        return "skipped"
    if case.find("failure") is not None:
        return "failed"
    if case.find("error") is not None:
        return "error"
    return "passed"


def parse_junit(path: Path) -> dict[str, str]:
    """Map testcase classname::name -> outcome (passed|failed|skipped|error|xfail)."""
    if not path.exists():
        return {}
    root = ET.parse(path).getroot()
    outcomes: dict[str, str] = {}
    for case in root.iter("testcase"):
        cls = case.get("classname") or ""
        name = case.get("name") or ""
        key = f"{cls}::{name}"
        skipped = case.find("skipped")
        if skipped is not None:
            msg = (skipped.get("message") or skipped.text or "").lower()
            if "xfail" in msg or "expected failure" in msg:
                outcomes[key] = "xfail"
            else:
                outcomes[key] = "skipped"
            continue
        outcomes[key] = _case_outcome(case)
    return outcomes


def _any_matching(outcomes: dict[str, str], *fragments: str) -> list[str]:
    hits: list[str] = []
    for key, outcome in outcomes.items():
        if all(f in key for f in fragments):
            hits.append(outcome)
    return hits


def aggregate_outcome(outcomes: list[str]) -> str | None:
    if not outcomes:
        return None
    if any(o in ("failed", "error") for o in outcomes):
        return "FAIL"
    if all(o == "xfail" for o in outcomes):
        return "XFAIL"
    if all(o in ("passed", "xfail", "skipped") for o in outcomes):
        if any(o == "xfail" for o in outcomes) and not any(o == "passed" for o in outcomes):
            return "XFAIL"
        return "PASS"
    return "FAIL"


def ipi_checklist_from_junit(
    outcomes: dict[str, str],
    *,
    slow_outcomes: dict[str, str] | None = None,
    unit_guard_passed: bool = False,
) -> dict[str, bool]:
    slow = slow_outcomes or {}
    merged = {**outcomes, **slow}

    def ok(*frags: str) -> bool:
        agg = aggregate_outcome(_any_matching(merged, *frags))
        return agg in ("PASS", "XFAIL")

    return {
        "3": ok("TestIPI01"),
        "4": ok("TestIPI02"),
        "5": ok("TestIPI03"),
        "6": ok("TestIPI04"),
        "7": ok("TestIPI05"),
        "8": ok("TestIPI06"),
        "10": ok("test_ipi_persistence_second_turn"),
        "11": ok("TestIPI01") and ok("TestIPI05"),
        "12": unit_guard_passed,
        "13": _failure_tags_documented(),
    }


def _failure_tags_documented() -> bool:
    judge = Path(__file__).resolve().parent.parent / "tests" / "helpers" / "ipi_judge.py"
    if not judge.exists():
        return False
    text = judge.read_text(encoding="utf-8")
    return "obeyed-instruction" in text or "parser-stripped" in text


def csf_checklist_from_junit(outcomes: dict[str, str]) -> dict[str, bool]:
    def ok(*frags: str) -> bool:
        agg = aggregate_outcome(_any_matching(outcomes, *frags))
        return agg in ("PASS", "XFAIL")

    return {
        "5": ok("TestCSF01"),
        "6": ok("TestCSF02"),
        "9": ok("TestCSF05"),
        "10": ok("TestCSF06"),
        "11": ok("TestCSFMustTreatNormally"),
    }


def ipi_row_results(
    outcomes: dict[str, str], slow_outcomes: dict[str, str] | None = None
) -> dict[str, dict[str, Any]]:
    slow = slow_outcomes or {}
    merged = {**outcomes, **slow}

    def row(test_id: str, *frags: str, note: str = "") -> dict[str, Any]:
        agg = aggregate_outcome(_any_matching(merged, *frags))
        result = agg or "PENDING"
        return {
            "result": result,
            "description": f"Live integration run — {test_id} ({result})",
            "issues": note if result == "XFAIL" else "",
        }

    i02 = aggregate_outcome(_any_matching(merged, "TestIPI02"))
    i02_note = "parser-stripped fixtures XFAIL per survival log" if i02 == "XFAIL" else ""

    return {
        "IPI-01": row("IPI-01", "TestIPI01"),
        "IPI-02": row("IPI-02", "TestIPI02", note=i02_note),
        "IPI-03": row("IPI-03", "TestIPI03"),
        "IPI-04": row("IPI-04", "TestIPI04"),
        "IPI-05": row("IPI-05", "TestIPI05"),
        "IPI-06": row("IPI-06", "TestIPI06"),
    }


def csf_row_results(outcomes: dict[str, str]) -> dict[str, dict[str, Any]]:
    def row(test_id: str, *frags: str) -> dict[str, Any]:
        agg = aggregate_outcome(_any_matching(outcomes, *frags))
        return {
            "result": agg or "PENDING",
            "description": f"Live integration run — {test_id} ({agg or 'PENDING'})",
            "issues": "",
        }

    return {
        "CSF-01": row("CSF-01", "TestCSF01"),
        "CSF-02": row("CSF-02", "TestCSF02"),
        "CSF-03": row("CSF-03", "TestCSF03"),
        "CSF-05": row("CSF-05", "TestCSF05"),
        "CSF-06": row("CSF-06", "TestCSF06"),
    }
