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
from packages.core.rag.llama_adapters.ingestion import LlamaIndexIngestionAdapter
from packages.core.rag.vectorstores.pinecone_store import PineconeVectorStore
from packages.core.storage.s3 import S3Storage

METRICS_TENANT_NCERT = "__ncert_global__"
_DEFAULT_SUBJECTS: Dict[int, List[str]] = {
    6: ["science", "mathematics", "social_science", "english", "hindi", "telugu"],
    7: ["science", "mathematics", "social_science", "english", "hindi", "telugu"],
    8: ["science", "mathematics", "social_science", "english", "hindi", "telugu"],
    9: ["science", "mathematics", "social_science", "english", "hindi", "telugu"],
    10: ["science", "mathematics", "social_science", "english", "hindi", "telugu"],
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


async def process_ncert_upload_background(
    document_id: str,
    run_id: str,
    file_content: bytes,
    pdf_password: Optional[str],
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
    # Session closed here — pool slot free during ingest_text.

    try:
        full_text, pages = _extract_pdf_text_and_pages(file_content, pdf_password)

        ns = getattr(settings, "NCERT_GLOBAL_PINECONE_NAMESPACE", "NcertDataGlobal")
        ctx_model = getattr(settings, "NCERT_GLOBAL_CONTEXT_MODEL", "gpt-4o-mini")
        emb_model = getattr(settings, "NCERT_GLOBAL_EMBEDDING_MODEL", "text-embedding-3-large")
        emb_dims = int(getattr(settings, "NCERT_GLOBAL_EMBEDDING_DIMENSIONS", 1024))

        static_meta: Dict[str, Any] = {
            "source": "ncert",
            "subject": subject,
            "class": class_num,
            "display_source": _display_source(class_num, subject, chapter_no, chapter_name),
            "topic": doc_title or _display_source(class_num, subject, chapter_no, chapter_name),
        }
        if content_hash:
            static_meta["content_hash"] = content_hash
        if chapter_no is not None:
            static_meta["chapter_no"] = int(chapter_no)
        if chapter_name:
            static_meta["chapter_name"] = chapter_name

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
) -> Tuple[NcertGlobalDocument, NcertGlobalIngestionRun]:
    if class_num < 6 or class_num > 10:
        raise ValueError("class must be between 6 and 10")
    subject_slug = validate_ncert_subject(class_num, subject)

    doc_id = uuid.uuid4()
    run_id = uuid.uuid4()
    skey = storage_key_for_ncert_document(doc_id)
    content_hash = hashlib.sha256(file_content).hexdigest()

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
    return doc, run
