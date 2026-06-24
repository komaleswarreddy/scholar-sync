#!/usr/bin/env python3
"""Verify diagram extraction quality for problem-solver bank and eval pool."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from packages.core.processing.problem_solver_extraction import (  # noqa: E402
    detect_corruption,
    is_meaningful_diagram_description,
    is_verified_diagram_problem,
    strip_diagram_blocks,
)

BANK_PATH = SCRIPTS / "problem_solver_question_bank.json"
POOL_PATH = SCRIPTS / "problem_solver_eval_pool.json"

Q29_GOLDEN_ID = "jee_april_2026-p8-q29"
Q36_GOLDEN_ID = "jee_jan_2026-p15-q36"
Q29_REQUIRED = (
    "P",
    "Q",
    "S",
    "2 kg",
    "1.5 kg",
    "g/2",
    "μ",
    "0.33",
    "[Diagram:",
)

CORRUPTION_RES = [
    re.compile(r"\(\s+and\s+\)", re.I),
    re.compile(r"kg\s+and\s+kg", re.I),
]


def _check_q29(text: str) -> list[str]:
    missing = [tok for tok in Q29_REQUIRED if tok not in text]
    if detect_corruption(text):
        missing.append("corruption_flags")
    return missing


def _check_q36_options_after_diagram(text: str) -> list[str]:
    issues: list[str] = []
    if "[Diagram:" not in text:
        issues.append("[Diagram:")
        return issues
    d_idx = text.index("[Diagram:")
    opt_idx = text.find("1. t P > t Q")
    if opt_idx < 0:
        opt_idx = text.find("t P > t Q")
    if opt_idx < 0:
        issues.append("options_tail")
    elif opt_idx < d_idx:
        issues.append("options_before_diagram")
    return issues


def main() -> int:
    failures: list[str] = []

    if not BANK_PATH.exists():
        print(f"Missing bank: {BANK_PATH}", file=sys.stderr)
        return 1
    if not POOL_PATH.exists():
        print(f"Missing pool: {POOL_PATH}", file=sys.stderr)
        return 1

    bank = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    pool = json.loads(POOL_PATH.read_text(encoding="utf-8"))
    bank_by_id = {q["id"]: q for q in bank["questions"]}

    q29_bank = bank_by_id.get(Q29_GOLDEN_ID)
    if not q29_bank:
        failures.append(f"Q29 golden bank id missing: {Q29_GOLDEN_ID}")
    else:
        missing = _check_q29(q29_bank["problem_text_normalized"])
        if missing:
            failures.append(f"Q29 bank golden check failed: missing {missing}")

    pool_q29 = [it for it in pool["items"] if it["id"] == Q29_GOLDEN_ID]
    if not pool_q29:
        failures.append(f"Q29 not in eval pool: {Q29_GOLDEN_ID}")
    else:
        for it in pool_q29:
            missing = _check_q29(it["problem_text_normalized"])
            if missing:
                failures.append(f"{it['example_id']}: Q29 pool golden check failed: missing {missing}")

    q36_bank = bank_by_id.get(Q36_GOLDEN_ID)
    if not q36_bank:
        failures.append(f"Q36 golden bank id missing: {Q36_GOLDEN_ID}")
    else:
        issues = _check_q36_options_after_diagram(q36_bank["problem_text_normalized"])
        if issues:
            failures.append(f"Q36 bank golden check failed: {issues}")

    pool_q36 = [it for it in pool["items"] if it["id"] == Q36_GOLDEN_ID]
    for it in pool_q36:
        issues = _check_q36_options_after_diagram(it["problem_text_normalized"])
        if issues:
            failures.append(f"{it['example_id']}: Q36 pool golden check failed: {issues}")

    for it in pool["items"]:
        text = it["problem_text_normalized"]
        for pat in CORRUPTION_RES:
            if pat.search(text):
                failures.append(f"{it['example_id']}: corruption pattern {pat.pattern}")
                break
        if it.get("variation") == "diagram" and not is_verified_diagram_problem(text):
            failures.append(f"{it['example_id']}: diagram variation not verified")
        if it.get("has_image") and not is_verified_diagram_problem(text):
            failures.append(f"{it['example_id']}: has_image but diagram not verified")
        if "[diagram:" in text.lower():
            import re as _re

            for block in _re.findall(r"\[Diagram:\s*([^\]]*)\]", text, flags=_re.I):
                if not is_meaningful_diagram_description(block):
                    failures.append(f"{it['example_id']}: text-only [Diagram:] block retained")
                    break
                if not is_verified_diagram_problem(text):
                    failures.append(f"{it['example_id']}: mismatched [Diagram:] block")
                    break

    print(f"Diagram extraction quality: {len(failures)} failure(s)")
    for f in failures[:20]:
        print(f"  FAIL: {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
