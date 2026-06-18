"""
Admin-only NCERT global knowledge upload and management.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, Request, UploadFile
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.routes.admin import check_admin_role
from apps.api.schemas.ncert_global import (
    NcertGlobalDocumentListResponse,
    NcertGlobalDocumentResponse,
    NcertGlobalIngestionRunListResponse,
    NcertGlobalIngestionRunResponse,
    NcertGlobalUploadAcceptedResponse,
)
from packages.core.database.connection import get_db
from packages.core.database.models.ncert_global import NcertGlobalDocument, NcertGlobalIngestionRun
from packages.core.services.ncert_global_service import (
    create_ncert_upload,
    delete_ncert_global_document_cascade,
    process_ncert_upload_background,
)

router = APIRouter()

MAX_NCERT_PDF_BYTES = 80 * 1024 * 1024


def _doc_to_response(doc: NcertGlobalDocument) -> NcertGlobalDocumentResponse:
    return NcertGlobalDocumentResponse(
        id=str(doc.id),
        class_num=int(doc.class_num),
        subject=doc.subject,
        chapter_no=doc.chapter_no,
        chapter_name=doc.chapter_name,
        title=doc.title,
        original_filename=doc.original_filename,
        storage_key=doc.storage_key,
        status=doc.status,
        chunks_count=int(doc.chunks_count or 0),
        error_message=doc.error_message,
        uploaded_by_clerk_user_id=doc.uploaded_by_clerk_user_id,
        pinecone_namespace=doc.pinecone_namespace,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.post("/ncert-global/documents", response_model=NcertGlobalUploadAcceptedResponse)
async def upload_ncert_global_document(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
    class_num: int = Form(..., ge=12, le=12),
    subject: str = Form(...),
    title: str = Form(""),
    chapter_no: Optional[int] = Form(None),
    chapter_name: Optional[str] = Form(None),
    pdf_password: Optional[str] = Form(None),
):
    if not await check_admin_role(
        request, db, raise_on_db_unavailable=True, db_timeout_s=25.0
    ):
        raise HTTPException(status_code=403, detail="Admin access required")

    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(content) > MAX_NCERT_PDF_BYTES:
        raise HTTPException(status_code=400, detail=f"File too large (max {MAX_NCERT_PDF_BYTES // (1024 * 1024)} MB)")

    fn = file.filename or "upload.pdf"
    if not (fn.lower().endswith(".pdf") or (file.content_type or "").lower() == "application/pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported for NCERT global ingest")

    try:
        doc, run = await create_ncert_upload(
            db,
            file_content=content,
            filename=fn,
            title=title or fn,
            class_num=class_num,
            subject=subject,
            chapter_no=chapter_no,
            chapter_name=chapter_name,
            uploaded_by_clerk_user_id=user_id,
            pdf_password=pdf_password,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    background_tasks.add_task(
        process_ncert_upload_background,
        str(doc.id),
        str(run.id),
        content,
        pdf_password,
    )

    return NcertGlobalUploadAcceptedResponse(
        document=_doc_to_response(doc),
        ingestion_run_id=str(run.id),
    )


@router.get("/ncert-global/documents", response_model=NcertGlobalDocumentListResponse)
async def list_ncert_global_documents(
    request: Request,
    db: AsyncSession = Depends(get_db),
    class_num: Optional[int] = Query(None, ge=12, le=12),
    subject: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    if not await check_admin_role(
        request, db, raise_on_db_unavailable=True, db_timeout_s=25.0
    ):
        raise HTTPException(status_code=403, detail="Admin access required")

    cq = select(func.count()).select_from(NcertGlobalDocument)
    if class_num is not None:
        cq = cq.where(NcertGlobalDocument.class_num == class_num)
    if subject:
        cq = cq.where(NcertGlobalDocument.subject == subject.strip().lower())
    if status:
        cq = cq.where(NcertGlobalDocument.status == status.strip().lower())
    total = int((await db.execute(cq)).scalar() or 0)

    q = select(NcertGlobalDocument).order_by(NcertGlobalDocument.created_at.desc())
    if class_num is not None:
        q = q.where(NcertGlobalDocument.class_num == class_num)
    if subject:
        q = q.where(NcertGlobalDocument.subject == subject.strip().lower())
    if status:
        q = q.where(NcertGlobalDocument.status == status.strip().lower())
    q = q.limit(limit)

    result = await db.execute(q)
    rows = result.scalars().all()
    return NcertGlobalDocumentListResponse(
        documents=[_doc_to_response(d) for d in rows],
        total=total,
    )


@router.get("/ncert-global/documents/{document_id}", response_model=NcertGlobalDocumentResponse)
async def get_ncert_global_document(
    request: Request,
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    if not await check_admin_role(
        request, db, raise_on_db_unavailable=True, db_timeout_s=25.0
    ):
        raise HTTPException(status_code=403, detail="Admin access required")
    try:
        did = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document id")
    r = await db.execute(select(NcertGlobalDocument).where(NcertGlobalDocument.id == did))
    doc = r.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return _doc_to_response(doc)


@router.delete("/ncert-global/documents/{document_id}")
async def delete_ncert_global_document(
    request: Request,
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    if not await check_admin_role(
        request, db, raise_on_db_unavailable=True, db_timeout_s=25.0
    ):
        raise HTTPException(status_code=403, detail="Admin access required")
    try:
        did = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document id")
    try:
        await delete_ncert_global_document_cascade(db, did)
    except ValueError:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True, "id": document_id}


@router.get("/ncert-global/ingestion-runs", response_model=NcertGlobalIngestionRunListResponse)
async def list_ncert_ingestion_runs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    document_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    if not await check_admin_role(
        request, db, raise_on_db_unavailable=True, db_timeout_s=25.0
    ):
        raise HTTPException(status_code=403, detail="Admin access required")

    q = select(NcertGlobalIngestionRun).order_by(NcertGlobalIngestionRun.started_at.desc())
    if document_id:
        try:
            q = q.where(NcertGlobalIngestionRun.document_id == uuid.UUID(document_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid document_id")
    q = q.limit(limit)
    result = await db.execute(q)
    runs = result.scalars().all()
    return NcertGlobalIngestionRunListResponse(
        runs=[NcertGlobalIngestionRunResponse.from_orm_run(r) for r in runs],
        total=len(runs),
    )


@router.get("/ncert-global/ingestion-runs/{run_id}", response_model=NcertGlobalIngestionRunResponse)
async def get_ncert_ingestion_run(
    request: Request,
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    if not await check_admin_role(
        request, db, raise_on_db_unavailable=True, db_timeout_s=25.0
    ):
        raise HTTPException(status_code=403, detail="Admin access required")
    try:
        rid = uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run id")
    r = await db.execute(select(NcertGlobalIngestionRun).where(NcertGlobalIngestionRun.id == rid))
    run = r.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Not found")
    return NcertGlobalIngestionRunResponse.from_orm_run(run)


@router.get("/ncert-global/subjects-by-class")
async def ncert_subjects_by_class(request: Request, db: AsyncSession = Depends(get_db)):
    """Allowed subject slugs per class for admin UI."""
    import asyncio

    from packages.core.services.ncert_global_service import load_ncert_subjects_by_class

    if not await check_admin_role(
        request, db, raise_on_db_unavailable=True, db_timeout_s=25.0
    ):
        raise HTTPException(status_code=403, detail="Admin access required")
    # Sync disk read — avoid blocking the event loop if YAML is large.
    return await asyncio.to_thread(load_ncert_subjects_by_class)
