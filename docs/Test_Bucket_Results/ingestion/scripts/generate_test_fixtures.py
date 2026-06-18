#!/usr/bin/env python3
"""
Generate synthetic fixtures for ING/RET integration tests.

Usage:
    python scripts/generate_test_fixtures.py
"""

from __future__ import annotations

import io
from pathlib import Path

from fpdf import FPDF
from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures" / "ingestion"


def _text_pdf_bytes(pages: list[str]) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    for text in pages:
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.multi_cell(0, 8, text)
    out = pdf.output()
    return out if isinstance(out, (bytes, bytearray)) else out.encode("latin-1")


def _write_text_pdf(path: Path, pages: list[str], *, encrypt_password: str | None = None) -> None:
    raw = _text_pdf_bytes(pages)
    if not encrypt_password:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return
    writer = PdfWriter()
    reader = PdfReader(io.BytesIO(raw))
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(encrypt_password)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        writer.write(fh)


def main() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)

    (FIXTURES / "sample_phrase_alpha.txt").write_text(
        "ING02_ALPHA_PHRASE: The mitochondria is the powerhouse of the cell.\n",
        encoding="utf-8",
    )
    (FIXTURES / "sample_phrase_beta.txt").write_text(
        "ING02_BETA_PHRASE: Snell's law relates angles of incidence and refraction.\n",
        encoding="utf-8",
    )

    chapter_pages = [
        "Chapter 1: Introduction to Photosynthesis.",
        "Photosynthesis converts light energy into chemical energy in plants.",
        "The key pigment chlorophyll absorbs red and blue light most effectively.",
        "Carbon dioxide and water are reactants in the Calvin cycle.",
        "RET_GOLDEN_FACT: The equation 6CO2 + 6H2O -> C6H12O6 + 6O2 summarizes photosynthesis.",
    ] + [f"Page {i}: filler content about plant biology and energy transfer." for i in range(6, 11)]

    _write_text_pdf(FIXTURES / "standard_chapter.pdf", chapter_pages)
    _write_text_pdf(
        FIXTURES / "encrypted_sample.pdf",
        ["Encrypted content phrase: RET_ENCRYPTED_SECRET_42."],
        encrypt_password="testpass",
    )

    large_pages = [f"Large document page {i}: Lorem ipsum dolor sit amet." for i in range(1, 51)]
    _write_text_pdf(FIXTURES / "large_50page.pdf", large_pages)

    standard_bytes = (FIXTURES / "standard_chapter.pdf").read_bytes()
    (FIXTURES / "truncated.pdf").write_bytes(standard_bytes[:200])
    (FIXTURES / "jpg_renamed.pdf").write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

    writer = PdfWriter()
    for _ in range(2):
        writer.add_blank_page(width=612, height=792)
    with (FIXTURES / "blank_scanned.pdf").open("wb") as fh:
        writer.write(fh)

    _write_text_pdf(
        FIXTURES / "physics_formulas.pdf",
        [
            "Snell's law: n1 sin(theta1) = n2 sin(theta2).",
            "Henderson-Hasselbalch equation: pH = pKa + log10([A-]/[HA]).",
            "Newton's second law: F = ma.",
        ],
    )

    print(f"Fixtures written to {FIXTURES}")


if __name__ == "__main__":
    main()
