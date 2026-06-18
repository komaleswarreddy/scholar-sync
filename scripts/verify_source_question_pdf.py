"""Verify English-only question extraction on a target PDF."""

from __future__ import annotations

import argparse
import asyncio
import re
from pathlib import Path

import pypdf

from packages.core.processing.image_ocr import extract_pdf_diagram_context
from packages.core.processing.question_regex_parser import regex_extract_questions
from packages.core.services.source_question_extraction_service import _filter_english_rows

DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")


def _read_pdf_text(pdf_path: Path) -> str:
    reader = pypdf.PdfReader(str(pdf_path))
    return "\n".join((page.extract_text() or "") for page in reader.pages).strip()


async def verify(pdf_path: Path, min_questions: int) -> int:
    text = _read_pdf_text(pdf_path)
    regex_rows = regex_extract_questions(text)
    english_rows = _filter_english_rows(regex_rows)
    diagram_context = await extract_pdf_diagram_context(pdf_path.read_bytes())
    hindi_rows = sum(
        1 for row in english_rows if DEVANAGARI_RE.search(str(row.get("full_text") or ""))
    )

    print(f"pdf: {pdf_path}")
    print(f"regex_rows: {len(regex_rows)}")
    print(f"english_rows: {len(english_rows)}")
    print(f"hindi_rows_after_filter: {hindi_rows}")
    print(f"diagram_context_chars: {len(diagram_context)}")
    if english_rows:
        print("sample_previews:")
        for row in english_rows[:5]:
            preview = str(row["preview"])[:120].encode("ascii", errors="replace").decode("ascii")
            print(f"  - Q{row['question_number']}: {preview}")

    if len(english_rows) < min_questions:
        print(f"[FAIL] extracted questions below threshold: {len(english_rows)} < {min_questions}")
        return 1
    if hindi_rows > 0:
        print(f"[FAIL] Hindi rows leaked after filter: {hindi_rows}")
        return 1

    print("[PASS] Extraction checks passed.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify extraction quality for one PDF")
    parser.add_argument("pdf_path", type=Path)
    parser.add_argument("--min-questions", type=int, default=10)
    args = parser.parse_args()

    if not args.pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {args.pdf_path}")

    exit_code = asyncio.run(verify(args.pdf_path, args.min_questions))
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
