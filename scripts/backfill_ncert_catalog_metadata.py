"""Backfill catalog concepts and topic summaries from document sketches."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings
from packages.core.cache.sketch_store import (
    RedisSketchStore,
    load_document_sketch,
    save_document_sketch_to_disk,
)
from packages.core.database.connection import AsyncSessionLocal, engine
from packages.core.database.models.ncert_catalog import NcertCatalogChapter
from packages.core.database.models.ncert_global import NcertGlobalDocument
from packages.core.rag.contextual_retrieval.document_sketcher import generate_ncert_document_sketch
from packages.core.services.ncert_catalog_helpers import (
    concepts_from_sketch,
    topic_summary_from_sketch,
)
from packages.core.services.ncert_constants import METRICS_TENANT_NCERT
from packages.core.services.ncert_global_service import _extract_pdf_text_and_pages, _display_source


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


async def _save_sketch(content_hash: str, sketch: dict) -> None:
    ttl = int(
        getattr(settings, "CONTEXTUAL_RETRIEVAL_NCERT_DOC_SKETCH_CACHE_TTL_SECONDS", 3600)
    )
    backend = str(
        getattr(settings, "CONTEXTUAL_RETRIEVAL_NCERT_DOC_SKETCH_CACHE_BACKEND", "disk") or "disk"
    ).strip().lower()
    save_document_sketch_to_disk(content_hash, sketch, ttl_seconds=ttl)
    if backend == "redis":
        try:
            await RedisSketchStore().set(content_hash, sketch, ttl_seconds=ttl)
        except Exception:
            pass


async def _generate_sketch_for_row(
    row: NcertCatalogChapter,
    doc: NcertGlobalDocument | None,
    pdf_root: Path | None,
) -> dict | None:
    pdf_path = resolve_pdf_path(row, pdf_root)
    if not pdf_path.exists():
        return None

    content = pdf_path.read_bytes()
    full_text, _pages = _extract_pdf_text_and_pages(content)
    header = _display_source(
        int(row.class_num),
        row.subject_slug,
        int(row.chapter_no),
        row.chapter_title,
    )
    model = (
        str(getattr(settings, "CONTEXTUAL_RETRIEVAL_NCERT_DOC_SKETCH_MODEL", "") or "").strip()
        or str(getattr(settings, "NCERT_GLOBAL_CONTEXT_MODEL", "gpt-4o-mini"))
    )
    sketch = await generate_ncert_document_sketch(
        tenant_id=METRICS_TENANT_NCERT,
        user_id=None,
        header=header,
        document_text=full_text,
        model=model,
        request_id=f"backfill-{row.id}",
        usage_accumulator=None,
    )
    if isinstance(sketch, dict) and doc and doc.content_hash:
        await _save_sketch(doc.content_hash, sketch)
    return sketch if isinstance(sketch, dict) else None


async def backfill(
    *,
    pdf_root: Path | None,
    limit: int | None,
    generate_missing: bool,
    only_missing: bool,
) -> None:
    updated = 0
    generated = 0
    skipped = 0
    failed = 0

    async with AsyncSessionLocal() as db:
        query = select(NcertCatalogChapter).order_by(
            NcertCatalogChapter.class_num,
            NcertCatalogChapter.subject_key,
            NcertCatalogChapter.chapter_no,
        )
        if only_missing:
            query = query.where(NcertCatalogChapter.concept_count == 0)
        result = await db.execute(query)
        rows = list(result.scalars().all())
        if limit:
            rows = rows[:limit]

        for row in rows:
            row_id = row.id
            class_num = int(row.class_num)
            subject_key = str(row.subject_key)
            chapter_no = int(row.chapter_no)
            try:
                doc = None
                content_hash = (row.content_hash or "").strip()
                if row.ncert_document_id:
                    doc_result = await db.execute(
                        select(NcertGlobalDocument).where(
                            NcertGlobalDocument.id == row.ncert_document_id
                        )
                    )
                    doc = doc_result.scalar_one_or_none()
                    if doc and doc.content_hash:
                        content_hash = doc.content_hash

                sketch = await load_document_sketch(content_hash) if content_hash else None
                if sketch is None and generate_missing:
                    if not settings.OPENAI_API_KEY:
                        print(
                            f"[SKIP] No sketch and OPENAI_API_KEY unset: "
                            f"class={class_num} {subject_key} ch{chapter_no}"
                        )
                        skipped += 1
                        continue
                    print(
                        f"[GEN] Generating sketch: class={class_num} "
                        f"{subject_key} ch{chapter_no}"
                    )
                    sketch = await _generate_sketch_for_row(row, doc, pdf_root)
                    if sketch:
                        generated += 1

                if not isinstance(sketch, dict):
                    skipped += 1
                    continue

                concepts = concepts_from_sketch(sketch)
                summary = topic_summary_from_sketch(sketch)
                changed = False

                if concepts and (not row.concepts or int(row.concept_count or 0) == 0):
                    row.concepts = concepts
                    row.concept_count = len(concepts)
                    changed = True
                if summary and not (row.topic_summary or "").strip():
                    row.topic_summary = summary
                    changed = True
                if row.ingest_status != "indexed" and row.ncert_document_id:
                    row.ingest_status = "indexed"
                    changed = True

                if changed:
                    await db.commit()
                    updated += 1
                    print(
                        f"[OK] class={class_num} {subject_key} ch={chapter_no} "
                        f"concepts={row.concept_count}"
                    )
                else:
                    skipped += 1
            except Exception as ex:
                await db.rollback()
                failed += 1
                print(
                    f"[FAIL] class={class_num} {subject_key} ch{chapter_no}: {ex}"
                )

    print(
        f"Backfill summary: updated={updated}, generated={generated}, "
        f"skipped={skipped}, failed={failed}"
    )
    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill NCERT catalog concepts/summaries")
    parser.add_argument(
        "--pdf-root",
        type=Path,
        default=PROJECT_ROOT / "NCERT_Class_9_10_PDFs",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--generate-missing",
        action="store_true",
        help="Generate sketches via LLM when not in Redis/disk cache",
    )
    parser.add_argument(
        "--only-missing",
        action="store_true",
        help="Only process rows with concept_count=0",
    )
    args = parser.parse_args()
    pdf_root = args.pdf_root if args.pdf_root.exists() else None
    asyncio.run(
        backfill(
            pdf_root=pdf_root,
            limit=args.limit,
            generate_missing=args.generate_missing,
            only_missing=args.only_missing,
        )
    )


if __name__ == "__main__":
    main()
