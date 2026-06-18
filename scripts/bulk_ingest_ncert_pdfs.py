"""Bulk-ingest NCERT Class 12 PDFs from catalog into the global NCERT pipeline."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.core.database.connection import AsyncSessionLocal, engine
from packages.core.database.models.ncert_catalog import NcertCatalogChapter
from packages.core.services.ncert_global_service import (
    create_ncert_upload,
    process_ncert_upload_background,
)

DEFAULT_UPLOADED_BY = "bulk-ingest-script"


async def bulk_ingest(
    *,
    pdf_root: Path | None,
    limit: int | None,
    skip_indexed: bool,
    run_background: bool,
    uploaded_by: str,
) -> None:
    ingested = 0
    skipped = 0
    failed = 0

    async with AsyncSessionLocal() as db:
        query = select(NcertCatalogChapter).order_by(
            NcertCatalogChapter.class_num,
            NcertCatalogChapter.subject_key,
            NcertCatalogChapter.chapter_no,
        )
        if skip_indexed:
            query = query.where(NcertCatalogChapter.ingest_status != "indexed")
        result = await db.execute(query)
        rows = list(result.scalars().all())
        if limit:
            rows = rows[:limit]

        for row in rows:
            pdf_path = Path(row.pdf_path or "")
            if pdf_root and row.filename:
                alt = pdf_root / f"Class {row.class_num}" / row.subject
                if row.subsubject:
                    alt = alt / row.subsubject
                alt = alt / row.filename
                if alt.exists():
                    pdf_path = alt
            if not pdf_path.exists():
                print(f"[SKIP] Missing PDF: {row.class_num} {row.subject_key} ch{row.chapter_no} -> {pdf_path}")
                skipped += 1
                continue

            try:
                content = pdf_path.read_bytes()
                ingest_subject = row.subject_slug
                doc, run = await create_ncert_upload(
                    db,
                    file_content=content,
                    filename=row.filename,
                    title=f"Ch. {row.chapter_no} · {row.chapter_title}",
                    class_num=int(row.class_num),
                    subject=ingest_subject,
                    chapter_no=int(row.chapter_no),
                    chapter_name=row.chapter_title,
                    uploaded_by_clerk_user_id=uploaded_by,
                    subsubject=row.subsubject,
                    catalog_chapter_id=row.id,
                )
                if doc.status == "indexed":
                    print(f"[SKIP] Already indexed: {row.subject_key} ch{row.chapter_no}")
                    skipped += 1
                    continue

                if run_background:
                    await process_ncert_upload_background(
                        str(doc.id),
                        str(run.id),
                        content,
                        None,
                        subsubject=row.subsubject,
                    )
                ingested += 1
                print(f"[OK] Ingested {row.class_num} {row.subject_key} ch{row.chapter_no} -> {doc.id}")
            except Exception as ex:
                failed += 1
                print(f"[FAIL] {row.class_num} {row.subject_key} ch{row.chapter_no}: {ex}")

    print(f"Bulk ingest summary: ingested={ingested}, skipped={skipped}, failed={failed}")
    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Bulk ingest NCERT PDFs from catalog")
    parser.add_argument("--pdf-root", type=Path, default=None, help="Override PDF root directory")
    parser.add_argument("--limit", type=int, default=None, help="Max chapters to process")
    parser.add_argument(
        "--include-indexed",
        action="store_true",
        help="Re-process chapters already marked indexed",
    )
    parser.add_argument(
        "--queue-only",
        action="store_true",
        help="Create upload rows only; do not run background ingest (for API worker)",
    )
    parser.add_argument("--uploaded-by", type=str, default=DEFAULT_UPLOADED_BY)
    args = parser.parse_args()

    asyncio.run(
        bulk_ingest(
            pdf_root=args.pdf_root,
            limit=args.limit,
            skip_indexed=not args.include_indexed,
            run_background=not args.queue_only,
            uploaded_by=args.uploaded_by,
        )
    )


if __name__ == "__main__":
    main()
