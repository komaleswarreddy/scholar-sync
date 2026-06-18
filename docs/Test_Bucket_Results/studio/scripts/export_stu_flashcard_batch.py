#!/usr/bin/env python3
"""
Export STU-04/05 flashcard batch for curriculum human review.

Usage:
  INTEGRATION_TESTS=1 python scripts/export_stu_flashcard_batch.py
  INTEGRATION_TESTS=1 python scripts/export_stu_flashcard_batch.py --target-count 100
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from packages.core.validation.studio_output_validators import validate_flashcards_schema  # noqa: E402
from tests.helpers.auth import make_dev_jwt  # noqa: E402
from tests.helpers.ingest_client import upload_file, wait_for_source_status  # noqa: E402
from tests.helpers.studio_client import generate_studio  # noqa: E402

GOLDEN = ROOT / "evals" / "datasets" / "stu_gold_chapters.json"
FIXTURES = ROOT / "tests" / "fixtures" / "ingestion"


def _card_count(data) -> int:
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        cards = data.get("cards") or data.get("flashcards") or []
        return len(cards) if isinstance(cards, list) else 0
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.getenv("NOTEBOOKLM_API_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--user-id", default="stu_flashcard_export_user")
    parser.add_argument("--target-count", type=int, default=100)
    parser.add_argument("--output", default="evals/reports/stu_flashcard_batch.json")
    args = parser.parse_args()

    if os.getenv("INTEGRATION_TESTS", "").strip() not in {"1", "true", "yes"}:
        print("Set INTEGRATION_TESTS=1 for live flashcard export")
        return 2

    chapters = json.loads(GOLDEN.read_text(encoding="utf-8")).get("chapters") or []
    token = make_dev_jwt(args.user_id)
    items: list[dict] = []
    total_cards = 0

    with httpx.Client(timeout=300.0) as client:
        for chapter in chapters:
            if total_cards >= args.target_count:
                break
            fixture = chapter.get("fixture_file") or "standard_chapter.pdf"
            path = FIXTURES / fixture
            if not path.exists():
                continue
            upload = upload_file(
                client,
                base_url=args.base_url,
                token=token,
                file_path=path,
                title=f"stu_flash_{chapter.get('id')}",
            )
            if upload.status_code != 200:
                continue
            source_id = upload.json()["id"]
            wait_for_source_status(client, base_url=args.base_url, token=token, source_id=source_id)

            result = generate_studio(
                client,
                base_url=args.base_url,
                token=token,
                task_type="flashcards",
                source_ids=[source_id],
            )
            data = result.body.get("data") if result.status_code == 200 else None
            structure = validate_flashcards_schema(data)
            count = _card_count(data)
            total_cards += count
            items.append(
                {
                    "chapter_id": chapter.get("id"),
                    "fixture_file": fixture,
                    "source_id": source_id,
                    "http_status": result.status_code,
                    "card_count": count,
                    "structure_valid": structure.valid,
                    "structure_errors": structure.errors,
                    "human_verified": None,
                    "correctness": None,
                    "formula_correct": None,
                    "failure_tag": None if structure.valid else "structure-error",
                    "flashcard_data": data,
                    "expected_formula_cards": chapter.get("formula_cards") or [],
                }
            )

    out_path = ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "bucket": "STU-04/05",
        "target_count": args.target_count,
        "total_cards_exported": total_cards,
        "items": items,
        "review_instructions": (
            "Review fact integrity (STU-04) and formula cards (STU-05). "
            "Set human_verified and correctness/formula_correct per item."
        ),
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(items)} flashcard runs ({total_cards} cards) to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
