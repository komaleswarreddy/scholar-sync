"""Audit NCERT catalog ingest health: row counts, PDFs, indexing, concepts."""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections import Counter, defaultdict
from pathlib import Path

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.core.database.connection import AsyncSessionLocal, engine
from packages.core.database.models.ncert_catalog import NcertCatalogChapter


def resolve_pdf_path(row: NcertCatalogChapter, pdf_root: Path | None) -> Path:
    pdf_path = Path(row.pdf_path or "")
    if pdf_root and row.filename:
        alt = pdf_root / f"Class {row.class_num}" / row.subject
        if row.subsubject:
            alt = alt / row.subsubject
        alt = alt / row.filename
        if alt.exists():
            return alt
    return pdf_path


async def audit(*, pdf_root: Path | None) -> int:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(NcertCatalogChapter).order_by(
                NcertCatalogChapter.class_num,
                NcertCatalogChapter.subject_key,
                NcertCatalogChapter.chapter_no,
            )
        )
        rows = list(result.scalars().all())

    total = len(rows)
    indexed = sum(1 for r in rows if r.ingest_status == "indexed")
    linked = sum(1 for r in rows if r.ncert_document_id is not None)
    with_concepts = sum(1 for r in rows if int(r.concept_count or 0) > 0)
    with_summary = sum(1 for r in rows if (r.topic_summary or "").strip())
    pdf_ok = 0
    pdf_missing: list[str] = []
    not_indexed: list[str] = []
    no_concepts: list[str] = []

    by_group: dict[str, Counter] = defaultdict(Counter)

    for row in rows:
        key = f"class={row.class_num} subject={row.subject_key}"
        by_group[key]["total"] += 1
        if row.ingest_status == "indexed":
            by_group[key]["indexed"] += 1
        if int(row.concept_count or 0) > 0:
            by_group[key]["concepts"] += 1

        pdf_path = resolve_pdf_path(row, pdf_root)
        if pdf_path.exists():
            pdf_ok += 1
        else:
            pdf_missing.append(
                f"  class={row.class_num} {row.subject_key} ch{row.chapter_no} -> {pdf_path}"
            )

        if row.ingest_status != "indexed":
            not_indexed.append(
                f"  class={row.class_num} {row.subject_key} ch{row.chapter_no} status={row.ingest_status}"
            )
        elif int(row.concept_count or 0) == 0:
            no_concepts.append(
                f"  class={row.class_num} {row.subject_key} ch{row.chapter_no}"
            )

    print("=== NCERT Catalog Audit ===")
    print(f"Catalog rows:           {total} (expected 93)")
    print(f"ingest_status=indexed:  {indexed}")
    print(f"ncert_document_id set:  {linked}")
    print(f"PDF file exists:        {pdf_ok}")
    print(f"concept_count > 0:      {with_concepts}")
    print(f"topic_summary set:      {with_summary}")
    print()
    print("--- By class / subject ---")
    for group in sorted(by_group.keys()):
        c = by_group[group]
        print(
            f"{group}: total={c['total']} indexed={c.get('indexed', 0)} "
            f"with_concepts={c.get('concepts', 0)}"
        )

    if pdf_missing:
        print(f"\n--- Missing PDFs ({len(pdf_missing)}) ---")
        for line in pdf_missing[:20]:
            print(line)
        if len(pdf_missing) > 20:
            print(f"  ... and {len(pdf_missing) - 20} more")

    if not_indexed:
        print(f"\n--- Not indexed ({len(not_indexed)}) ---")
        for line in not_indexed[:20]:
            print(line)
        if len(not_indexed) > 20:
            print(f"  ... and {len(not_indexed) - 20} more")

    if no_concepts:
        print(f"\n--- Indexed but no concepts ({len(no_concepts)}) ---")
        for line in no_concepts[:20]:
            print(line)
        if len(no_concepts) > 20:
            print(f"  ... and {len(no_concepts) - 20} more")

    await engine.dispose()

    ok = total == 93 and indexed == 93 and pdf_ok == 93 and with_concepts == 93
    print()
    if ok:
        print("RESULT: PASS (all 93 chapters indexed, PDFs present, concepts populated)")
        return 0
    if total == 93 and indexed == 93 and pdf_ok == 93:
        print("RESULT: PARTIAL (indexed + PDFs OK; run backfill for concepts/summaries)")
        return 1
    print("RESULT: FAIL (ingest or PDF gaps remain)")
    return 2


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit NCERT catalog ingest health")
    parser.add_argument(
        "--pdf-root",
        type=Path,
        default=PROJECT_ROOT / "NCERT_Class_9_10_PDFs",
        help="PDF root directory",
    )
    args = parser.parse_args()
    pdf_root = args.pdf_root if args.pdf_root.exists() else None
    code = asyncio.run(audit(pdf_root=pdf_root))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
