#!/usr/bin/env python3
"""
Batch ING-08 rubric export for 10 fixture sources (5 chunks each).

Usage:
  INTEGRATION_TESTS=1 python scripts/export_ing08_batch.py
  INTEGRATION_TESTS=1 python scripts/export_ing08_batch.py --output evals/reports/ing08_rubric_batch.json
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from tests.helpers.auth import make_dev_jwt  # noqa: E402
from tests.helpers.ingest_client import upload_file, wait_for_source_status  # noqa: E402
from tests.helpers.pinecone_helpers import chunk_texts, fetch_source_chunks  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "ingestion"
RUBRIC = [
    "complete_sentences",
    "semantic_coherence",
    "reasonable_overlap",
    "formula_equation_integrity",
]

BATCH_FIXTURES = [
    "standard_chapter.pdf",
    "physics_formulas.pdf",
    "sample_phrase_alpha.txt",
    "sample_phrase_beta.txt",
    "large_50page.pdf",
    "encrypted_sample.pdf",
    "blank_scanned.pdf",
    "truncated.pdf",
    "jpg_renamed.pdf",
    "standard_chapter.pdf",
]


def _sample_chunks(tenant_id: str, source_id: str, samples: int) -> list[dict]:
    chunks = fetch_source_chunks(tenant_id=tenant_id, source_id=source_id, top_k=200)
    texts = chunk_texts(chunks)
    if not texts:
        return []
    picked = random.sample(texts, min(samples, len(texts)))
    rows = []
    for i, text in enumerate(picked, start=1):
        rows.append(
            {
                "chunk_index": i,
                "text_preview": text[:500],
                "scores": {criterion: None for criterion in RUBRIC},
                "pass": None,
                "reviewer_notes": "",
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.getenv("NOTEBOOKLM_API_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--tenant-id", default=os.getenv("NOTEBOOKLM_TENANT_ID", "eeff7c1c-fe22-4573-ad93-a36f19ad4dc5"))
    parser.add_argument("--user-id", default="ing08_batch_user")
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--output", default="evals/reports/ing08_rubric_batch.json")
    args = parser.parse_args()

    if os.getenv("INTEGRATION_TESTS", "").strip() not in {"1", "true", "yes"}:
        print("Set INTEGRATION_TESTS=1 for live rubric export")
        return 2

    token = make_dev_jwt(args.user_id)
    sources: list[dict] = []

    with httpx.Client(timeout=120.0) as client:
        for name in BATCH_FIXTURES:
            path = FIXTURES / name
            if not path.exists():
                continue
            kwargs = {}
            if name == "encrypted_sample.pdf":
                kwargs["pdf_password"] = "testpass"
            try:
                response = upload_file(
                    client, base_url=args.base_url, token=token, file_path=path, **kwargs
                )
                if response.status_code != 200:
                    continue
                source_id = response.json()["id"]
                wait_for_source_status(
                    client, base_url=args.base_url, token=token, source_id=source_id
                )
                chunk_rows = _sample_chunks(args.tenant_id, source_id, args.samples)
                if chunk_rows:
                    sources.append(
                        {
                            "fixture_file": name,
                            "source_id": source_id,
                            "samples": chunk_rows,
                        }
                    )
            except Exception as exc:  # noqa: BLE001
                sources.append({"fixture_file": name, "error": str(exc), "samples": []})

    payload = {
        "test_id": "ING-08",
        "pass_threshold": 0.90,
        "tenant_id": args.tenant_id,
        "rubric_criteria": RUBRIC,
        "sources": sources,
        "instructions": "Score each sample 1=pass 0=fail per criterion. pass=all four pass.",
        "status": "PENDING",
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote ING-08 batch rubric ({len(sources)} sources) to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
