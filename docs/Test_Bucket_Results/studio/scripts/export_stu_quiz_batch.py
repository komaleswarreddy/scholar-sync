#!/usr/bin/env python3
"""
Export STU-01/02 quiz batch for curriculum human review.

Usage:
  INTEGRATION_TESTS=1 python scripts/export_stu_quiz_batch.py
  INTEGRATION_TESTS=1 python scripts/export_stu_quiz_batch.py --output evals/reports/stu_quiz_batch.json
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

from packages.core.validation.studio_output_validators import validate_quiz_schema  # noqa: E402
from tests.helpers.auth import make_dev_jwt  # noqa: E402
from tests.helpers.ingest_client import upload_file, wait_for_source_status  # noqa: E402
from tests.helpers.studio_client import generate_studio  # noqa: E402

GOLDEN = ROOT / "evals" / "datasets" / "stu_gold_chapters.json"
FIXTURES = ROOT / "tests" / "fixtures" / "ingestion"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.getenv("NOTEBOOKLM_API_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--user-id", default="stu_quiz_export_user")
    parser.add_argument("--quizzes-per-chapter", type=int, default=1)
    parser.add_argument("--output", default="evals/reports/stu_quiz_batch.json")
    args = parser.parse_args()

    if os.getenv("INTEGRATION_TESTS", "").strip() not in {"1", "true", "yes"}:
        print("Set INTEGRATION_TESTS=1 for live quiz export")
        return 2

    if not GOLDEN.exists():
        print(f"Missing dataset: {GOLDEN}")
        return 2

    chapters = json.loads(GOLDEN.read_text(encoding="utf-8")).get("chapters") or []
    token = make_dev_jwt(args.user_id)
    items: list[dict] = []
    errors: list[dict] = []

    with httpx.Client(timeout=300.0) as client:
        for chapter in chapters:
            fixture = chapter.get("fixture_file") or "standard_chapter.pdf"
            path = FIXTURES / fixture
            if not path.exists():
                errors.append({"chapter_id": chapter.get("id"), "error": f"missing fixture {fixture}"})
                continue
            upload = upload_file(
                client,
                base_url=args.base_url,
                token=token,
                file_path=path,
                title=f"stu_quiz_{chapter.get('id')}",
            )
            if upload.status_code != 200:
                errors.append(
                    {"chapter_id": chapter.get("id"), "error": f"upload {upload.status_code}"}
                )
                continue
            source_id = upload.json()["id"]
            wait_for_source_status(client, base_url=args.base_url, token=token, source_id=source_id)

            for n in range(args.quizzes_per_chapter):
                result = generate_studio(
                    client,
                    base_url=args.base_url,
                    token=token,
                    task_type="quiz",
                    source_ids=[source_id],
                )
                quiz_data = result.body.get("data") if result.status_code == 200 else None
                structure = validate_quiz_schema(quiz_data)
                items.append(
                    {
                        "chapter_id": chapter.get("id"),
                        "fixture_file": fixture,
                        "source_id": source_id,
                        "run_index": n + 1,
                        "http_status": result.status_code,
                        "structure_valid": structure.valid,
                        "structure_errors": structure.errors,
                        "human_verified": None,
                        "correctness": None,
                        "ambiguity_flag": None,
                        "failure_tag": None if structure.valid else "structure-error",
                        "quiz_data": quiz_data,
                        "expected_facts": chapter.get("expected_facts") or [],
                    }
                )

    out_path = ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "bucket": "STU-01/02",
        "items": items,
        "errors": errors,
        "review_instructions": (
            "Set human_verified=true, correctness=true/false, ambiguity_flag=true/false per item. "
            "Run scripts/verify_studio_curriculum_signoff.py when complete."
        ),
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(items)} quiz items to {out_path}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
