#!/usr/bin/env python3
"""
ING-08 manual rubric exporter.

Samples random chunks per ingested source for Curriculum manual scoring.
Target: >=90% of chunks pass all four criteria (complete sentences, semantic coherence,
reasonable overlap, formula/equation integrity).

Usage:
  python scripts/rubric_ing08_chunk_quality.py --tenant-id <uuid> --source-id <uuid> --samples 5
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.helpers.pinecone_helpers import chunk_texts, fetch_source_chunks  # noqa: E402

RUBRIC = [
    "complete_sentences",
    "semantic_coherence",
    "reasonable_overlap",
    "formula_equation_integrity",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--output", default="evals/reports/ing08_rubric_sample.json")
    args = parser.parse_args()

    chunks = fetch_source_chunks(tenant_id=args.tenant_id, source_id=args.source_id, top_k=200)
    texts = chunk_texts(chunks)
    if not texts:
        print("No chunks found")
        return 1

    sample = random.sample(texts, min(args.samples, len(texts)))
    rows = []
    for i, text in enumerate(sample, start=1):
        rows.append(
            {
                "chunk_index": i,
                "text_preview": text[:500],
                "scores": {criterion: None for criterion in RUBRIC},
                "pass": None,
                "reviewer_notes": "",
            }
        )

    payload = {
        "test_id": "ING-08",
        "pass_threshold": 0.90,
        "source_id": args.source_id,
        "tenant_id": args.tenant_id,
        "rubric_criteria": RUBRIC,
        "samples": rows,
        "instructions": "Score each sample 1=pass 0=fail per criterion. pass=all four pass.",
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out} — complete manual scoring in spreadsheet or JSON.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
