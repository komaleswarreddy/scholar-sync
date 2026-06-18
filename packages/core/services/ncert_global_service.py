"""
Admin NCERT global corpus: Supabase storage, Pinecone namespace NcertDataGlobal, ingestion runs + costs.
"""

from __future__ import annotations

import hashlib
import io
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pypdf
import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from packages.core.database.models.ncert_global import NcertGlobalDocument, NcertGlobalIngestionRun
from packages.core.processing.context_cache import ContextCache
from packages.core.processing.pdf_preprocessor import PDFPreprocessor
from packages.core.rag.llama_adapters.ingestion import LlamaIndexIngestionAdapter
from packages.core.rag.vectorstores.pinecone_store import PineconeVectorStore
from packages.core.services.ncert_constants import METRICS_TENANT_NCERT
from packages.core.storage.s3 import S3Storage
_DEFAULT_SUBJECTS: Dict[int, List[str]] = {
    12: ["physics", "chemistry", "mathematics", "biology"],
}


def load_ncert_subjects_by_class() -> Dict[int, List[str]]:
    p = Path(__file__).resolve().parents[3] / "config" / "ncert_subjects_by_class.yaml"
    if not p.exists():
        return dict(_DEFAULT_SUBJECTS)
    try:
        with open(p, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        out: Dict[int, List[str]] = {}
        for k, v in raw.items():
            try:
                out[int(k)] = [str(s).strip().lower() for s in (v or [])]
            except (TypeError, ValueError):
                continue
        return out or dict(_DEFAULT_SUBJECTS)
    except Exception:
        return dict(_DEFAULT_SUBJECTS)


def validate_ncert_subject(class_num: int, subject: str) -> str:
    subject_slug = (subject or "").strip().lower().replace(" ", "_")
    allowed = load_ncert_subjects_by_class().get(class_num, [])
    if subject_slug not in allowed:
        raise ValueError(
            f"Subject '{subject}' is not allowed for class {class_num}. Allowed: {', '.join(allowed)}"
        )
    return subject_slug


def _extract_pdf_text_and_pages(
    file_content: bytes, pdf_password: Optional[str] = None
) -> Tuple[str, List[Tuple[int, str]]]:
    pdf_reader = pypdf.PdfReader(io.BytesIO(file_content))
    if pdf_reader.is_encrypted:
        if pdf_password:
            if not pdf_reader.decrypt(pdf_password):
                raise ValueError("Incorrect password for PDF.")
        else:
            if not pdf_reader.decrypt(""):
                raise ValueError("PDF is password-protected. Provide pdf_password.")
    pages: List[Tuple[int, str]] = []
    full_text = ""
    for page_num, page in enumerate(pdf_reader.pages, start=1):
        try:
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages.append((page_num, page_text))
                full_text += page_text + "\n\n"
        except Exception as e:
            print(f"[NCERT] Page {page_num} extract warning: {e}")
    if not full_text.strip():
        raise ValueError("PDF contains no extractable text.")
    return full_text.strip(), pages


def _display_source(
    class_num: int, subject_slug: str, chapter_no: Optional[int], chapter_name: Optional[str]
) -> str:
    subj = subject_slug.replace("_", " ").title()
    if chapter_no is not None and (chapter_name or "").strip():
        return f"NCERT Class {class_num} {subj} — Ch.{chapter_no}: {chapter_name.strip()}"
    if chapter_no is not None:
        return f"NCERT Class {class_num} {subj} — Ch.{chapter_no}"
    return f"NCERT Class {class_num} {subj}"


def storage_key_for_ncert_document(document_id: uuid.UUID) -> str:
    return f"global/ncert/{document_id}.pdf"


async def _persist_ncert_ingest_success(
    doc_uuid: uuid.UUID,
    run_uuid: uuid.UUID,
    usage: Dict[str, Any],
    nodes_indexed: int,
) -> None:
    from packages.core.database.connection import AsyncSessionLocal

    total_cost = float(usage.get("context_llm_cost_usd", 0.0)) + float(
        usage.get("embedding_cost_usd", 0.0)
    )
    async with AsyncSessionLocal() as db:
        doc_result = await db.execute(
            select(NcertGlobalDocument).where(NcertGlobalDocument.id == doc_uuid)
        )
        doc = doc_result.scalar_one_or_none()
        run_result = await db.execute(
            select(NcertGlobalIngestionRun).where(NcertGlobalIngestionRun.id == run_uuid)
        )
        run = run_result.scalar_one_or_none()
        if not run or not doc:
            print(f"[NCERT] Missing doc/run on success persist: doc={doc_uuid} run={run_uuid}")
            return
        run.status = "success"
        run.completed_at = datetime.now(timezone.utc)
        run.context_llm_prompt_tokens = int(usage.get("context_llm_prompt_tokens", 0))
        run.context_llm_completion_tokens = int(usage.get("context_llm_completion_tokens", 0))
        run.context_llm_cost_usd = Decimal(str(round(usage.get("context_llm_cost_usd", 0.0), 6)))
        run.embedding_prompt_tokens = int(usage.get("embedding_prompt_tokens", 0))
        run.embedding_cost_usd = Decimal(str(round(usage.get("embedding_cost_usd", 0.0), 6)))
        run.total_cost_usd = Decimal(str(round(total_cost, 6)))
        run.chunks_processed = nodes_indexed
        run.error_message = None
        doc.status = "indexed"
        doc.chunks_count = nodes_indexed
        doc.error_message = None
        await db.commit()

    await sync_catalog_from_document(doc_uuid)


async def _persist_ncert_ingest_failure(
    doc_uuid: uuid.UUID,
    run_uuid: uuid.UUID,
    usage: Dict[str, Any],
    err: str,
) -> None:
    from packages.core.database.connection import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            doc_result = await db.execute(
                select(NcertGlobalDocument).where(NcertGlobalDocument.id == doc_uuid)
            )
            doc = doc_result.scalar_one_or_none()
            run_result = await db.execute(
                select(NcertGlobalIngestionRun).where(NcertGlobalIngestionRun.id == run_uuid)
            )
            run = run_result.scalar_one_or_none()
            if run:
                run.status = "failed"
                run.completed_at = datetime.now(timezone.utc)
                run.error_message = err[:2000]
                run.context_llm_prompt_tokens = int(usage.get("context_llm_prompt_tokens", 0))
                run.context_llm_completion_tokens = int(usage.get("context_llm_completion_tokens", 0))
                run.context_llm_cost_usd = Decimal(str(round(usage.get("context_llm_cost_usd", 0.0), 6)))
                run.embedding_prompt_tokens = int(usage.get("embedding_prompt_tokens", 0))
                run.embedding_cost_usd = Decimal(str(round(usage.get("embedding_cost_usd", 0.0), 6)))
                run.total_cost_usd = Decimal(
                    str(
                        round(
                            float(usage.get("context_llm_cost_usd", 0.0))
                            + float(usage.get("embedding_cost_usd", 0.0)),
                            6,
                        )
                    )
                )
            if doc:
                doc.status = "error"
                doc.error_message = err[:2000]
            await db.commit()
        except Exception as e2:
            print(f"[NCERT] Failed to persist error state: {e2}")
            await db.rollback()


async def sync_catalog_from_document(doc_uuid: uuid.UUID) -> None:
    """Link catalog chapter row and persist document-sketch concepts after ingest."""
    from packages.core.cache.sketch_store import load_document_sketch
    from packages.core.database.connection import AsyncSessionLocal
    from packages.core.database.models.ncert_catalog import NcertCatalogChapter
    from packages.core.services.ncert_catalog_helpers import (
        concepts_from_sketch,
        topic_summary_from_sketch,
    )

    async with AsyncSessionLocal() as db:
        doc_result = await db.execute(
            select(NcertGlobalDocument).where(NcertGlobalDocument.id == doc_uuid)
        )
        doc = doc_result.scalar_one_or_none()
        if not doc:
            return

        catalog = None
        if doc.chapter_no is not None:
            # Match by class + chapter + subject slug (social science sub-books share slug).
            result = await db.execute(
                select(NcertCatalogChapter).where(
                    NcertCatalogChapter.class_num == int(doc.class_num),
                    NcertCatalogChapter.chapter_no == int(doc.chapter_no),
                    NcertCatalogChapter.subject_slug == doc.subject,
                )
            )
            rows = list(result.scalars().all())
            if len(rows) == 1:
                catalog = rows[0]
            elif doc.chapter_name:
                ch_name = doc.chapter_name.strip().lower()
                for row in rows:
                    if (row.chapter_title or "").strip().lower() == ch_name:
                        catalog = row
                        break
                if catalog is None and rows:
                    catalog = rows[0]

        if catalog is None and doc.content_hash:
            result = await db.execute(
                select(NcertCatalogChapter).where(
                    NcertCatalogChapter.content_hash == doc.content_hash
                )
            )
            catalog = result.scalar_one_or_none()

        if catalog is None:
            return

        sketch = None
        if doc.content_hash:
            try:
                sketch = await load_document_sketch(doc.content_hash)
            except Exception as ex:
                print(f"[NCERT] Catalog sketch read warning: {ex}")

        concepts = concepts_from_sketch(sketch)
        summary = topic_summary_from_sketch(sketch)

        catalog.ncert_document_id = doc.id
        catalog.content_hash = doc.content_hash
        catalog.ingest_status = "indexed"
        if concepts:
            catalog.concepts = concepts
            catalog.concept_count = len(concepts)
        if summary and not catalog.topic_summary:
            catalog.topic_summary = summary

        await db.commit()
        print(
            f"[NCERT] Catalog synced: class={catalog.class_num} "
            f"key={catalog.subject_key} ch={catalog.chapter_no} concepts={catalog.concept_count}"
        )


async def process_ncert_upload_background(
    document_id: str,
    run_id: str,
    file_content: bytes,
    pdf_password: Optional[str],
    subsubject: Optional[str] = None,
) -> None:
    """Background: extract, contextualize, embed into NcertDataGlobal; update DB + run costs.

    DB connections are held only for short read/write bursts. Heavy work (LLM, embeddings,
    Pinecone) runs **without** an open session so the pool is not blocked during long ingests
    (avoids 503s on admin routes that share the same Supabase pool).
    """
    from packages.core.database.connection import AsyncSessionLocal

    doc_uuid = uuid.UUID(document_id)
    run_uuid = uuid.UUID(run_id)
    usage: Dict[str, Any] = {
        "context_llm_prompt_tokens": 0,
        "context_llm_completion_tokens": 0,
        "context_llm_cost_usd": 0.0,
        "embedding_prompt_tokens": 0,
        "embedding_cost_usd": 0.0,
    }

    async with AsyncSessionLocal() as db:
        doc_result = await db.execute(
            select(NcertGlobalDocument).where(NcertGlobalDocument.id == doc_uuid)
        )
        doc = doc_result.scalar_one_or_none()
        run_result = await db.execute(
            select(NcertGlobalIngestionRun).where(NcertGlobalIngestionRun.id == run_uuid)
        )
        run = run_result.scalar_one_or_none()
        if not doc or not run:
            print(f"[NCERT] Missing document or run row: doc={document_id} run={run_id}")
            return
        # Snapshot ORM fields; release connection before long-running ingest.
        uploaded_by = doc.uploaded_by_clerk_user_id
        subject = doc.subject
        class_num = int(doc.class_num)
        chapter_no = doc.chapter_no
        chapter_name = doc.chapter_name
        doc_title = (doc.title or "").strip()
        content_hash = (doc.content_hash or "").strip()
        doc_subsubject = subsubject
    # Session closed here — pool slot free during ingest_text.

    context_cache = ContextCache(cache_dir="cache/processed_pdfs/ncert_global")
    pdf_preprocessor = PDFPreprocessor()

    try:
        cached_content = context_cache.get_cached_content(
            file_content,
            tenant_id=METRICS_TENANT_NCERT,
            user_id=uploaded_by,
        )
        if cached_content:
            chunks_with_metadata = [
                (chunk_text, {**metadata, "source_id": document_id})
                for chunk_text, metadata in cached_content["chunks"]
            ]
            ns = getattr(settings, "NCERT_GLOBAL_PINECONE_NAMESPACE", "NcertDataGlobal")
            ctx_model = getattr(settings, "NCERT_GLOBAL_CONTEXT_MODEL", "gpt-4o-mini")
            emb_model = getattr(settings, "NCERT_GLOBAL_EMBEDDING_MODEL", "text-embedding-3-large")
            emb_dims = int(getattr(settings, "NCERT_GLOBAL_EMBEDDING_DIMENSIONS", 1024))
            static_meta: Dict[str, Any] = {
                "source": "ncert",
                "subject": subject.lower(),
                "class": class_num,
                "display_source": _display_source(class_num, subject, chapter_no, chapter_name),
                "topic": doc_title or _display_source(class_num, subject, chapter_no, chapter_name),
            }
            if content_hash:
                static_meta["content_hash"] = content_hash
            if chapter_no is not None:
                static_meta["chapter_no"] = int(chapter_no)
            if chapter_name:
                static_meta["chapter_name"] = chapter_name.lower()
            if doc_subsubject:
                static_meta["subsubject"] = str(doc_subsubject).strip().lower()
            adapter = LlamaIndexIngestionAdapter(
                METRICS_TENANT_NCERT,
                user_id=uploaded_by,
                pinecone_namespace=ns,
                embedding_model=emb_model,
                embedding_dimensions=emb_dims,
                contextual_llm_model=ctx_model,
                ingestion_run_id=str(run_uuid),
                static_chunk_metadata=static_meta,
                metrics_tenant_id=METRICS_TENANT_NCERT,
                usage_accumulator=usage,
            )
            result = await adapter.ingest_chunks(
                source_id=document_id,
                chunks_with_metadata=chunks_with_metadata,
            )
            await _persist_ncert_ingest_success(doc_uuid, run_uuid, usage, result.nodes_indexed)
            return

        full_text, pages = _extract_pdf_text_and_pages(file_content, pdf_password)
        if pages:
            try:
                cleaned = pdf_preprocessor.clean_text(full_text, pages)
                print(
                    f"[NCERT] PDFPreprocessor: {len(full_text)} -> {len(cleaned)} chars "
                    f"({100 * (1 - len(cleaned) / max(len(full_text), 1)):.1f}% reduction)"
                )
                full_text = cleaned
            except Exception as prep_err:
                print(f"[WARNING] NCERT PDF preprocessing failed, using raw text: {prep_err}")

        ns = getattr(settings, "NCERT_GLOBAL_PINECONE_NAMESPACE", "NcertDataGlobal")
        ctx_model = getattr(settings, "NCERT_GLOBAL_CONTEXT_MODEL", "gpt-4o-mini")
        emb_model = getattr(settings, "NCERT_GLOBAL_EMBEDDING_MODEL", "text-embedding-3-large")
        emb_dims = int(getattr(settings, "NCERT_GLOBAL_EMBEDDING_DIMENSIONS", 1024))

        static_meta: Dict[str, Any] = {
            "source": "ncert",
            "subject": subject.lower(),  # Normalize to lowercase for consistent filtering
            "class": class_num,
            "display_source": _display_source(class_num, subject, chapter_no, chapter_name),
            "topic": doc_title or _display_source(class_num, subject, chapter_no, chapter_name),
        }
        if content_hash:
            static_meta["content_hash"] = content_hash
        if chapter_no is not None:
            static_meta["chapter_no"] = int(chapter_no)
        if chapter_name:
            static_meta["chapter_name"] = chapter_name.lower()  # Normalize to lowercase for consistent filtering
        if doc_subsubject:
            static_meta["subsubject"] = str(doc_subsubject).strip().lower()


        adapter = LlamaIndexIngestionAdapter(
            METRICS_TENANT_NCERT,
            user_id=uploaded_by,
            pinecone_namespace=ns,
            embedding_model=emb_model,
            embedding_dimensions=emb_dims,
            contextual_llm_model=ctx_model,
            ingestion_run_id=str(run_uuid),
            static_chunk_metadata=static_meta,
            metrics_tenant_id=METRICS_TENANT_NCERT,
            usage_accumulator=usage,
        )

        result = await adapter.ingest_text(
            text=full_text,
            source_id=document_id,
            pages=pages,
        )

        if result.chunks_for_cache:
            try:
                context_cache.cache_content(
                    file_content,
                    full_text,
                    result.chunks_for_cache,
                    metadata={
                        "content_type": "application/pdf",
                        "page_count": len(pages) if pages else 0,
                        "source": "ncert",
                    },
                )
            except Exception as cache_err:
                print(f"[WARNING] NCERT context cache write failed: {cache_err}")

        await _persist_ncert_ingest_success(doc_uuid, run_uuid, usage, result.nodes_indexed)
    except Exception as e:
        import traceback

        err = f"{type(e).__name__}: {e}"
        print(f"[NCERT] Ingestion failed {document_id}: {err}\n{traceback.format_exc()}")
        await _persist_ncert_ingest_failure(doc_uuid, run_uuid, usage, err)


async def delete_ncert_global_document_cascade(db: AsyncSession, document_id: uuid.UUID) -> None:
    """Remove Pinecone vectors, Supabase object, DB rows (ingestion runs cascade)."""
    result = await db.execute(select(NcertGlobalDocument).where(NcertGlobalDocument.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise ValueError("NCERT document not found")

    ns = doc.pinecone_namespace or getattr(settings, "NCERT_GLOBAL_PINECONE_NAMESPACE", "NcertDataGlobal")
    sid = str(document_id)

    try:
        vs = PineconeVectorStore(METRICS_TENANT_NCERT, namespace_override=ns)
        await vs.delete_vectors_by_source(sid)
    except Exception as e:
        print(f"[NCERT] Pinecone delete warning for {sid}: {e}")

    try:
        storage = S3Storage(tenant_id="global")
        await storage.delete_file(doc.storage_key)
    except Exception as e:
        print(f"[NCERT] Storage delete warning for {doc.storage_key}: {e}")

    await db.delete(doc)
    await db.commit()


async def create_ncert_upload(
    db: AsyncSession,
    *,
    file_content: bytes,
    filename: str,
    title: str,
    class_num: int,
    subject: str,
    chapter_no: Optional[int],
    chapter_name: Optional[str],
    uploaded_by_clerk_user_id: str,
    pdf_password: Optional[str] = None,
    subsubject: Optional[str] = None,
    catalog_chapter_id: Optional[uuid.UUID] = None,
) -> Tuple[NcertGlobalDocument, NcertGlobalIngestionRun]:
    if class_num != 12:
        raise ValueError("class must be 12")
    subject_slug = validate_ncert_subject(class_num, subject)

    content_hash = hashlib.sha256(file_content).hexdigest()

    existing = await db.execute(
        select(NcertGlobalDocument).where(NcertGlobalDocument.content_hash == content_hash)
    )
    existing_doc = existing.scalar_one_or_none()
    if existing_doc:
        if catalog_chapter_id:
            from packages.core.database.models.ncert_catalog import NcertCatalogChapter

            cat_result = await db.execute(
                select(NcertCatalogChapter).where(NcertCatalogChapter.id == catalog_chapter_id)
            )
            catalog = cat_result.scalar_one_or_none()
            if catalog:
                catalog.ncert_document_id = existing_doc.id
                catalog.content_hash = content_hash
                catalog.ingest_status = (
                    "indexed" if existing_doc.status == "indexed" else existing_doc.status
                )
                await db.commit()
        run_result = await db.execute(
            select(NcertGlobalIngestionRun)
            .where(NcertGlobalIngestionRun.document_id == existing_doc.id)
            .order_by(NcertGlobalIngestionRun.started_at.desc())
            .limit(1)
        )
        run = run_result.scalars().first()
        if run is None:
            run = NcertGlobalIngestionRun(
                id=uuid.uuid4(),
                document_id=existing_doc.id,
                status=existing_doc.status,
            )
            db.add(run)
            await db.commit()
            await db.refresh(run)
        return existing_doc, run

    doc_id = uuid.uuid4()
    run_id = uuid.uuid4()
    skey = storage_key_for_ncert_document(doc_id)

    doc = NcertGlobalDocument(
        id=doc_id,
        class_num=class_num,
        subject=subject_slug,
        chapter_no=chapter_no,
        chapter_name=(chapter_name or "").strip() or None,
        title=title.strip() or filename,
        original_filename=filename,
        storage_key=skey,
        content_hash=content_hash,
        status="processing",
        chunks_count=0,
        uploaded_by_clerk_user_id=uploaded_by_clerk_user_id,
        pinecone_namespace=getattr(settings, "NCERT_GLOBAL_PINECONE_NAMESPACE", "NcertDataGlobal"),
    )
    run = NcertGlobalIngestionRun(
        id=run_id,
        document_id=doc_id,
        status="running",
    )
    db.add(doc)
    db.add(run)

    storage = S3Storage(tenant_id="global")
    await storage.upload_file_bytes(
        file_content,
        skey,
        "application/pdf" if filename.lower().endswith(".pdf") else "application/octet-stream",
    )
    await db.commit()
    await db.refresh(doc)
    await db.refresh(run)

    if catalog_chapter_id:
        from packages.core.database.models.ncert_catalog import NcertCatalogChapter

        cat_result = await db.execute(
            select(NcertCatalogChapter).where(NcertCatalogChapter.id == catalog_chapter_id)
        )
        catalog = cat_result.scalar_one_or_none()
        if catalog:
            catalog.ncert_document_id = doc.id
            catalog.content_hash = content_hash
            catalog.ingest_status = "processing"
            await db.commit()

    return doc, run
