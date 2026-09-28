"""Tutor Mode catalog and featured notebook endpoints."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.schemas.tutor_bootstrap import (
    TutorBootstrapResponse,
    TutorFollowUpsRequest,
    TutorFollowUpsResponse,
)
from apps.api.schemas.tutor_prepare import (
    TutorNcertWarmRequest,
    TutorNcertWarmResponse,
    TutorPrepareRequest,
    TutorPrepareResponse,
    TutorPrepareTiming,
)
from packages.core.database.connection import get_db
from packages.core.database.models.ncert_global import NcertGlobalDocument
from packages.core.services.notebook_service import NotebookService
from packages.core.services.tutor_catalog_service import TutorCatalogService
from packages.core.services.tutor_notebook_bootstrap_service import TutorNotebookBootstrapService
from packages.core.services.tutor_notebook_prepare_service import TutorNotebookPrepareService
from packages.core.storage import get_storage_service
from apps.api.utils.safe_errors import safe_detail

router = APIRouter()


def _get_context(request: Request):
    tenant_id = getattr(request.state, "tenant_id", None)
    user_id = getattr(request.state, "user_id", None)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Tenant context not found")
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")
    return tenant_id, user_id


@router.get("/catalog")
async def get_tutor_catalog(
    request: Request,
    class_num: int = Query(..., ge=12, le=12),
    subject: Optional[str] = Query(default=None, description="Subject key, e.g. science"),
    chapter_no: Optional[int] = Query(default=None, ge=1),
    db: AsyncSession = Depends(get_db),
):
    service = TutorCatalogService(db)
    if subject is None:
        subjects = await service.list_subjects(class_num)
        return {"subjects": subjects}

    if chapter_no is None:
        chapters = await service.list_chapters(class_num, subject)
        return {"chapters": chapters}

    concepts = await service.list_concepts(class_num, subject, chapter_no)
    return {"concepts": concepts}


@router.get("/featured-notebooks")
async def get_featured_notebooks(
    request: Request,
    class_num: int = Query(..., ge=12, le=12),
    subject: str = Query(..., description="Subject key"),
    chapter_no: int = Query(..., ge=1),
    db: AsyncSession = Depends(get_db),
):
    tenant_id, user_id = _get_context(request)
    service = TutorCatalogService(db)
    notebooks = await service.list_featured_notebooks(
        tenant_id=tenant_id,
        user_id=user_id,
        class_num=class_num,
        subject_key=subject,
        chapter_no=chapter_no,
    )
    return {"notebooks": notebooks}


@router.get("/ncert-documents/{document_id}/file")
async def get_ncert_document_file(
    request: Request,
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Stream an indexed NCERT global PDF for tutor notebook source preview."""
    _get_context(request)
    try:
        did = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document id")

    result = await db.execute(select(NcertGlobalDocument).where(NcertGlobalDocument.id == did))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="NCERT document not found")
    if doc.status != "indexed":
        raise HTTPException(status_code=409, detail="NCERT document is not ready yet")

    storage = get_storage_service(tenant_id="global")
    try:
        content = await storage.download_file(doc.storage_key)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=safe_detail(exc, "Could not load NCERT PDF")) from exc

    filename = doc.original_filename or f"ncert-{document_id}.pdf"
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "private, max-age=3600",
        },
    )


@router.post("/notebooks/prepare", response_model=TutorPrepareResponse)
async def prepare_tutor_notebook(
    request: Request,
    body: TutorPrepareRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create tutor notebook with bootstrap summary, suggestions, and 2 parallel studio assets."""
    tenant_id, user_id = _get_context(request)
    service = TutorNotebookPrepareService(db, tenant_id, user_id)
    scope_dict = body.tutor_scope.model_dump()
    try:
        result = await service.prepare_notebook(
            title=body.title,
            tutor_scope=scope_dict,
            class_level=body.class_level,
            subject=body.subject,
            focus=body.focus,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=safe_detail(exc, "Prepare failed")) from exc

    timing_raw = result.get("timing") or {}
    return TutorPrepareResponse(
        notebook_id=result["notebook_id"],
        slug=result["slug"],
        opening_summary=result["opening_summary"],
        suggestions=result["suggestions"],
        studio_recommendations=result["studio_recommendations"],
        chat_id=result.get("chat_id"),
        assets_created=result.get("assets_created", 0),
        assets=result.get("assets") or [],
        auto_types=result.get("auto_types") or [],
        timing=TutorPrepareTiming(**timing_raw),
        partial_failure=bool(result.get("partial_failure")),
    )


@router.post("/ncert-context/warm", response_model=TutorNcertWarmResponse)
async def warm_tutor_ncert_context(
    request: Request,
    body: TutorNcertWarmRequest,
    db: AsyncSession = Depends(get_db),
):
    """Prefetch NCERT context for a chapter scope into cache (non-blocking warm on chapter select)."""
    tenant_id, user_id = _get_context(request)
    service = TutorNotebookPrepareService(db, tenant_id, user_id)
    try:
        meta = await service.warm_ncert_context(body.tutor_scope.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=safe_detail(exc, "Warm failed")) from exc
    return TutorNcertWarmResponse(
        ok=True,
        cached=bool(meta.get("cached")),
        context_chars=int(meta.get("context_chars") or 0),
        duration_ms=int(meta.get("duration_ms") or 0),
    )


@router.post("/notebooks/{notebook_id}/bootstrap", response_model=TutorBootstrapResponse)
async def bootstrap_tutor_notebook(
    request: Request,
    notebook_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Generate tutor notebook opening summary, suggestions, and studio plan."""
    tenant_id, user_id = _get_context(request)
    notebook_service = NotebookService(db, tenant_id, user_id)
    notebook = await notebook_service.get_notebook(notebook_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")
    if notebook.mode != "tutor":
        raise HTTPException(status_code=400, detail="Bootstrap is only for tutor notebooks")

    service = TutorNotebookBootstrapService(db, tenant_id, user_id)
    try:
        result = await service.bootstrap_notebook(notebook_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=safe_detail(exc, "Bootstrap failed")) from exc

    return TutorBootstrapResponse(**result)


@router.post("/follow-ups", response_model=TutorFollowUpsResponse)
async def tutor_follow_ups(
    request: Request,
    body: TutorFollowUpsRequest,
    db: AsyncSession = Depends(get_db),
):
    """Suggest context-specific follow-up questions after a tutor chat turn."""
    tenant_id, user_id = _get_context(request)
    service = TutorNotebookBootstrapService(db, tenant_id, user_id)
    follow_ups = await service.generate_follow_ups(
        notebook_id=body.notebook_id,
        user_message=body.user_message,
        assistant_message=body.assistant_message,
    )
    return TutorFollowUpsResponse(follow_ups=follow_ups)


@router.post("/notebooks/{notebook_id}/studio-generation-started")
async def mark_studio_generation_started(
    request: Request,
    notebook_id: str,
    db: AsyncSession = Depends(get_db),
):
    tenant_id, user_id = _get_context(request)
    service = TutorNotebookBootstrapService(db, tenant_id, user_id)
    await service.mark_studio_generation_started(notebook_id)
    return {"ok": True}
