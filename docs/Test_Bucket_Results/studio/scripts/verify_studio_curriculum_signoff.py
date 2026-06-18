#!/usr/bin/env python3
"""
Verify curriculum manual sign-off for STU-01/02/04/05 export artifacts.

Thresholds:
  - STU-01 quiz correctness >= 95%
  - STU-04 flashcard fact integrity >= 95%
  - STU-05 formula correctness >= 98% (formula-tagged items only)

Writes evals/reports/stu_curriculum_signoff_summary.json on success.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUIZ_PATH = ROOT / "evals" / "reports" / "stu_quiz_batch.json"
FLASH_PATH = ROOT / "evals" / "reports" / "stu_flashcard_batch.json"
SUMMARY_PATH = ROOT / "evals" / "reports" / "stu_curriculum_signoff_summary.json"

STU01_THRESHOLD = 0.95
STU04_THRESHOLD = 0.95
STU05_THRESHOLD = 0.98


def _load(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def verify_quiz(data: dict) -> tuple[bool, str, dict]:
    items = data.get("items") or []
    if not items:
        return False, "STU-01/02: no quiz items in batch", {}
    reviewed = [i for i in items if i.get("human_verified") is not None]
    if len(reviewed) < len(items):
        return False, f"STU-01/02: {len(items) - len(reviewed)} items missing human_verified", {}
    correct = sum(1 for i in items if i.get("correctness") is True)
    rate = correct / len(items)
    meta = {"total": len(items), "correct": correct, "rate": round(rate, 4), "threshold": STU01_THRESHOLD}
    if rate < STU01_THRESHOLD:
        return False, f"STU-01 correctness {rate:.1%} < {STU01_THRESHOLD:.0%}", meta
    return True, "STU-01/02 curriculum sign-off OK", meta


def verify_flashcards(data: dict) -> tuple[bool, str, dict]:
    items = data.get("items") or []
    if not items:
        return False, "STU-04/05: no flashcard items in batch", {}
    reviewed = [i for i in items if i.get("human_verified") is not None]
    if len(reviewed) < len(items):
        return False, f"STU-04/05: {len(items) - len(reviewed)} items missing human_verified", {}
    fact_ok = sum(1 for i in items if i.get("correctness") is True)
    fact_rate = fact_ok / len(items)
    formula_items = [i for i in items if i.get("expected_formula_cards")]
    formula_reviewed = [i for i in formula_items if i.get("formula_correct") is not None]
    formula_meta = {"total": len(formula_items), "reviewed": len(formula_reviewed)}
    if formula_items and len(formula_reviewed) < len(formula_items):
        return False, "STU-05: formula cards not fully reviewed", formula_meta
    formula_ok = sum(1 for i in formula_items if i.get("formula_correct") is True)
    formula_rate = (formula_ok / len(formula_items)) if formula_items else 1.0
    meta = {
        "stu04_rate": round(fact_rate, 4),
        "stu04_threshold": STU04_THRESHOLD,
        "stu05_rate": round(formula_rate, 4),
        "stu05_threshold": STU05_THRESHOLD,
    }
    if fact_rate < STU04_THRESHOLD:
        return False, f"STU-04 fact rate {fact_rate:.1%} < {STU04_THRESHOLD:.0%}", meta
    if formula_items and formula_rate < STU05_THRESHOLD:
        return False, f"STU-05 formula rate {formula_rate:.1%} < {STU05_THRESHOLD:.0%}", meta
    return True, "STU-04/05 curriculum sign-off OK", meta


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quiz", default=str(QUIZ_PATH))
    parser.add_argument("--flashcards", default=str(FLASH_PATH))
    args = parser.parse_args()

    quiz_data = _load(Path(args.quiz))
    flash_data = _load(Path(args.flashcards))
    ok_quiz, msg_quiz, meta_quiz = verify_quiz(quiz_data)
    ok_flash, msg_flash, meta_flash = verify_flashcards(flash_data)

    summary = {
        "stu01_02": {"pass": ok_quiz, "message": msg_quiz, **meta_quiz},
        "stu04_05": {"pass": ok_flash, "message": msg_flash, **meta_flash},
        "pass": ok_quiz and ok_flash,
    }
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    if not summary["pass"]:
        print("Studio curriculum sign-off FAILED", file=sys.stderr)
        return 1
    print("Studio curriculum sign-off OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
