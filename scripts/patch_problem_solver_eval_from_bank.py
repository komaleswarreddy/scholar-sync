#!/usr/bin/env python3
"""Patch eval pool problem_text_normalized from vision-enriched question bank."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

BANK_PATH = SCRIPTS / "problem_solver_question_bank.json"
POOL_PATH = SCRIPTS / "problem_solver_eval_pool.json"
PATCHED_IDS_PATH = SCRIPTS / "problem_solver_vision_patched_ids.json"


def _normalize(s: str) -> str:
    s = re.sub(r"\s+", " ", s.strip().lower())
    s = re.sub(r"^q\d+\.\s*", "", s)
    return s


def _jaccard(a: str, b: str) -> float:
    ta = set(re.findall(r"[a-z0-9]+", _normalize(a)))
    tb = set(re.findall(r"[a-z0-9]+", _normalize(b)))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _match_bank_item(
    item: dict,
    by_id: dict[str, dict],
    by_page: dict[tuple[str, int], list[dict]],
) -> dict | None:
    bank_q = by_id.get(item["id"])
    if bank_q:
        return bank_q
    candidates = by_page.get((item["source_key"], int(item["page"])), [])
    if not candidates:
        return None
    return max(candidates, key=lambda q: _jaccard(item["problem_text_normalized"], q["problem_text_normalized"]))


def main() -> int:
    parser = argparse.ArgumentParser(description="Patch eval pool from question bank")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not BANK_PATH.exists():
        print(f"Missing bank: {BANK_PATH}", file=sys.stderr)
        return 1
    if not POOL_PATH.exists():
        print(f"Missing pool: {POOL_PATH}", file=sys.stderr)
        return 1

    bank = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    pool = json.loads(POOL_PATH.read_text(encoding="utf-8"))
    by_id = {q["id"]: q for q in bank["questions"]}
    by_page: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for q in bank["questions"]:
        by_page[(q["source_key"], int(q["page"]))].append(q)

    patched_ids: list[str] = []
    patched_example_ids: list[str] = []
    for item in pool["items"]:
        bank_q = _match_bank_item(item, by_id, by_page)
        if not bank_q:
            continue
        if not (item.get("has_image") or bank_q.get("has_image") or bank_q.get("format") == "diagram"):
            continue
        new_text = bank_q["problem_text_normalized"]
        if new_text != item["problem_text_normalized"] or item["id"] != bank_q["id"]:
            patched_ids.append(item["id"])
            patched_example_ids.append(item["example_id"])
            if not args.dry_run:
                item["id"] = bank_q["id"]
                item["problem_text_normalized"] = new_text
                item["has_image"] = bank_q.get("has_image", item.get("has_image", False))
                if bank_q.get("diagram_description"):
                    item["diagram_description"] = bank_q["diagram_description"]
                item["extraction_method"] = bank_q.get("extraction_method", item.get("extraction_method"))

    if not args.dry_run:
        pool["version"] = "1.4.0"
        pool["extraction_tag"] = "vision_enriched_extraction"
        POOL_PATH.write_text(json.dumps(pool, indent=2, ensure_ascii=False), encoding="utf-8")
        PATCHED_IDS_PATH.write_text(
            json.dumps(
                {
                    "patched_problem_ids": list(dict.fromkeys(patched_ids)),
                    "patched_example_ids": list(dict.fromkeys(patched_example_ids)),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    print(f"Patched {len(patched_example_ids)} eval pool items")
    if patched_ids[:5]:
        print("Sample:", ", ".join(patched_ids[:5]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
