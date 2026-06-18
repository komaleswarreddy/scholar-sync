#!/usr/bin/env python3
"""Generate ret04_questions.txt (50 factual questions) from retrieval_golden.json."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "evals" / "datasets" / "retrieval_golden.json"
OUT = ROOT / "evals" / "datasets" / "ret04_questions.txt"


def main() -> int:
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    chapter_fixture = "standard_chapter.pdf"
    skip_substrings = ("filler pages", "mitochondria")
    factual = [
        it["question"]
        for it in golden["items"]
        if it.get("bucket") == "factual"
        and not it.get("negative")
        and chapter_fixture in (it.get("fixture_files") or [])
        and not any(s in (it.get("question") or "").lower() for s in skip_substrings)
    ]
    questions = factual[:50]
    while len(questions) < 50 and factual:
        questions.extend(factual[: 50 - len(questions)])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(questions[:50]) + "\n", encoding="utf-8")
    print(f"Wrote {len(questions[:50])} questions to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
