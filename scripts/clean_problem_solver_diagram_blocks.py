#!/usr/bin/env python3
"""Strip text-only [Diagram: ...] blocks from question bank and eval pool."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from packages.core.processing.problem_solver_extraction import (  # noqa: E402
    clean_problem_text_diagrams,
    filter_diagram_description,
    strip_diagram_blocks,
)

BANK_PATH = SCRIPTS / "problem_solver_question_bank.json"
POOL_PATH = SCRIPTS / "problem_solver_eval_pool.json"


def _clean_record(text: str, diagram_desc: str = "") -> tuple[str, str]:
    cleaned = clean_problem_text_diagrams(text, diagram_desc)
    desc = filter_diagram_description(diagram_desc)
    if "[diagram:" in cleaned.lower():
        return cleaned, desc
    return cleaned, ""


def clean_bank(dry_run: bool = False) -> dict[str, int]:
    bank = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    stats = {"total": 0, "changed": 0, "stripped_diagram": 0}
    for q in bank.get("questions", []):
        stats["total"] += 1
        old = q.get("problem_text_normalized", "")
        new, new_desc = _clean_record(old, q.get("diagram_description", ""))
        if new != old:
            stats["changed"] += 1
            if "[diagram:" in old.lower() and "[diagram:" not in new.lower():
                stats["stripped_diagram"] += 1
            if not dry_run:
                q["problem_text_normalized"] = new
                q["diagram_description"] = new_desc
                q["has_image"] = "[diagram:" in new.lower()
    if not dry_run:
        bank["version"] = "1.4.1"
        BANK_PATH.write_text(json.dumps(bank, indent=2, ensure_ascii=False), encoding="utf-8")
    return stats


def clean_pool(dry_run: bool = False) -> dict[str, int]:
    pool = json.loads(POOL_PATH.read_text(encoding="utf-8"))
    stats = {"total": 0, "changed": 0}
    for item in pool.get("items", []):
        stats["total"] += 1
        old = item.get("problem_text_normalized", "")
        new = strip_diagram_blocks(old)
        new = clean_problem_text_diagrams(new, item.get("diagram_description", ""))
        if new != old:
            stats["changed"] += 1
            if not dry_run:
                item["problem_text_normalized"] = new
                item["has_image"] = "[diagram:" in new.lower()
    if not dry_run:
        pool["version"] = "1.4.1"
        POOL_PATH.write_text(json.dumps(pool, indent=2, ensure_ascii=False), encoding="utf-8")
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean bogus diagram blocks from problem solver data")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not BANK_PATH.exists():
        print(f"Missing {BANK_PATH}", file=sys.stderr)
        return 1

    bank_stats = clean_bank(dry_run=args.dry_run)
    print(f"Bank: {bank_stats}")

    if POOL_PATH.exists():
        pool_stats = clean_pool(dry_run=args.dry_run)
        print(f"Pool: {pool_stats}")

    if args.dry_run:
        print("Dry run — no files written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
