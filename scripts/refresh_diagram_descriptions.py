#!/usr/bin/env python3
"""Re-apply diagram descriptions from vision cache with per-question matching."""

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
    merge_problem_and_diagram,
    pick_diagram_for_question,
    problem_likely_needs_diagram,
    should_attach_diagram,
    strip_diagram_blocks,
)

BANK_PATH = SCRIPTS / "problem_solver_question_bank.json"
POOL_PATH = SCRIPTS / "problem_solver_eval_pool.json"
CACHE_PATH = SCRIPTS / "problem_solver_vision_extract_cache.json"


def _page_diagram_desc(cache: dict, source_key: str, page: int) -> str:
    entry = cache.get("pages", {}).get(f"{source_key}-p{page}", {})
    return (entry.get("diagram_desc") or "").strip()


def refresh_bank(dry_run: bool = False) -> dict[str, int]:
    bank = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8")) if CACHE_PATH.exists() else {"pages": {}}
    stats = {"total": 0, "changed": 0, "diagram_added": 0, "diagram_removed": 0}

    for q in bank.get("questions", []):
        stats["total"] += 1
        old = q.get("problem_text_normalized", "")
        page_desc = q.get("diagram_description") or _page_diagram_desc(cache, q["source_key"], int(q["page"]))
        page_has_images = bool(page_desc) or bool(q.get("has_image")) or q.get("format") == "diagram"
        new = clean_problem_text_diagrams(
            old,
            page_desc,
            page_has_images=page_has_images,
        )
        picked = pick_diagram_for_question(strip_diagram_blocks(old), page_desc)
        if picked and should_attach_diagram(strip_diagram_blocks(old), picked, page_has_images=page_has_images):
            new = merge_problem_and_diagram(strip_diagram_blocks(old), picked, page_has_images=page_has_images)

        if new != old:
            stats["changed"] += 1
            if "[diagram:" in new.lower() and "[diagram:" not in old.lower():
                stats["diagram_added"] += 1
            if "[diagram:" in old.lower() and "[diagram:" not in new.lower():
                stats["diagram_removed"] += 1
            if not dry_run:
                q["problem_text_normalized"] = new
                q["diagram_description"] = picked or pick_diagram_for_question(strip_diagram_blocks(old), page_desc)
                q["has_image"] = "[diagram:" in new.lower()
                if q["has_image"] and q.get("format") not in ("diagram",):
                    if problem_likely_needs_diagram(strip_diagram_blocks(old)):
                        q["format"] = "diagram"

    if not dry_run:
        bank["version"] = "1.4.2"
        BANK_PATH.write_text(json.dumps(bank, indent=2, ensure_ascii=False), encoding="utf-8")
    return stats


def refresh_pool(dry_run: bool = False) -> dict[str, int]:
    bank = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    bank_by_id = {q["id"]: q for q in bank["questions"]}
    pool = json.loads(POOL_PATH.read_text(encoding="utf-8"))
    stats = {"total": 0, "changed": 0}

    for item in pool.get("items", []):
        stats["total"] += 1
        bank_q = bank_by_id.get(item["id"])
        if not bank_q:
            continue
        old = item.get("problem_text_normalized", "")
        new = bank_q["problem_text_normalized"]
        if new != old:
            stats["changed"] += 1
            if not dry_run:
                item["problem_text_normalized"] = new
                item["has_image"] = bank_q.get("has_image", False)
                if bank_q.get("format") == "diagram":
                    item["format"] = "diagram"

    if not dry_run:
        pool["version"] = "1.4.2"
        POOL_PATH.write_text(json.dumps(pool, indent=2, ensure_ascii=False), encoding="utf-8")
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh diagram descriptions from vision cache")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not BANK_PATH.exists():
        print(f"Missing {BANK_PATH}", file=sys.stderr)
        return 1

    bank_stats = refresh_bank(dry_run=args.dry_run)
    print(f"Bank: {bank_stats}")
    if POOL_PATH.exists():
        pool_stats = refresh_pool(dry_run=args.dry_run)
        print(f"Pool: {pool_stats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
