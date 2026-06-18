"""Seed ncert_catalog_chapters from a Class 12 inventory CSV."""

from __future__ import annotations

import asyncio
import csv
import sys
from pathlib import Path

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.core.database.connection import AsyncSessionLocal, engine
from packages.core.database.models.ncert_catalog import NcertCatalogChapter
from packages.core.services.ncert_catalog_helpers import (
    parse_chapter_from_filename,
    parse_class_num,
    resolve_pdf_path,
    subject_key_from_row,
    subject_slug_from_row,
)

DEFAULT_CSV = PROJECT_ROOT / "class 12" / "folder_inventory.csv"


async def seed_catalog(*, csv_path: Path, pdf_root: Path | None) -> None:
    if not csv_path.exists():
        raise FileNotFoundError(f"Inventory CSV not found: {csv_path}")

    inserted = 0
    updated = 0
    skipped = 0

    async with AsyncSessionLocal() as session:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if (row.get("valid_pdf") or "").strip().lower() != "true":
                    skipped += 1
                    continue

                class_num = parse_class_num(row.get("class") or "")
                if class_num != 12:
                    skipped += 1
                    continue

                subject = (row.get("subject") or "").strip()
                subsubject = (row.get("subsubject") or "").strip() or None
                filename = (row.get("filename") or "").strip()
                chapter_no, chapter_title = parse_chapter_from_filename(filename)
                subject_key = subject_key_from_row(subject, subsubject)
                subject_slug = subject_slug_from_row(subject)
                pdf_path = resolve_pdf_path(row.get("path") or "", pdf_root)
                hash_prefix = (row.get("sha256_16") or "").strip() or None

                result = await session.execute(
                    select(NcertCatalogChapter).where(
                        NcertCatalogChapter.class_num == class_num,
                        NcertCatalogChapter.subject_key == subject_key,
                        NcertCatalogChapter.chapter_no == chapter_no,
                    )
                )
                existing = result.scalar_one_or_none()

                if existing:
                    existing.subject = subject
                    existing.subsubject = subsubject
                    existing.subject_slug = subject_slug
                    existing.chapter_title = chapter_title
                    existing.filename = filename
                    existing.pdf_path = pdf_path
                    existing.content_hash_prefix = hash_prefix
                    updated += 1
                else:
                    session.add(
                        NcertCatalogChapter(
                            class_num=class_num,
                            subject=subject,
                            subsubject=subsubject,
                            subject_key=subject_key,
                            subject_slug=subject_slug,
                            chapter_no=chapter_no,
                            chapter_title=chapter_title,
                            filename=filename,
                            pdf_path=pdf_path,
                            content_hash_prefix=hash_prefix,
                            concepts=[],
                            concept_count=0,
                            featured_count=0,
                            is_featured_chapter=False,
                            ingest_status="pending",
                        )
                    )
                    inserted += 1

        await session.commit()

    print(f"Catalog seed complete: inserted={inserted}, updated={updated}, skipped={skipped}")
    await engine.dispose()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Seed NCERT catalog from folder_inventory.csv")
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV,
        help="Path to folder_inventory.csv",
    )
    parser.add_argument(
        "--pdf-root",
        type=Path,
        default=PROJECT_ROOT / "class 12",
        help="Root folder for PDF paths (rewrites CSV absolute paths)",
    )
    args = parser.parse_args()
    pdf_root = args.pdf_root if args.pdf_root.exists() else None
    asyncio.run(seed_catalog(csv_path=args.csv, pdf_root=pdf_root))


if __name__ == "__main__":
    main()
