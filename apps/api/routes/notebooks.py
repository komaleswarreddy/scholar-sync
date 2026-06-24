"""Notebook API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.schemas.notebook import (
    NotebookCreateRequest,
    NotebookUpdateRequest,
    NotebookResponse,
    NotebookDetailResponse,
    NotebookListItemResponse,
    NotebookListResponse,
)
from packages.core.database.connection import get_db
from packages.core.services.notebook_service import NotebookService, DEFAULT_NOTEBOOK_TITLE

router = APIRouter()


def _get_context(request: Request):
    tenant_id = getattr(request.state, "tenant_id", None)
    user_id = getattr(request.state, "user_id", None)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Tenant context not found")
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")
    return tenant_id, user_id


def _to_response(notebook) -> NotebookResponse:
    return NotebookResponse(
        id=str(notebook.id),
        title=notebook.title,
        slug=notebook.slug,
        mode=notebook.mode,
        subtitle=notebook.subtitle,
        subject=notebook.subject,
        class_level=notebook.class_level,
        focus=notebook.focus,
        mastery_percent=notebook.mastery_percent,
        created_at=notebook.created_at,
        updated_at=notebook.updated_at,
        last_studied_at=notebook.last_studied_at,
    )


@router.post("", response_model=NotebookResponse)
async def create_notebook(
    body: NotebookCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id, user_id = _get_context(request)
    service = NotebookService(db, tenant_id, user_id)
    notebook = await service.create_notebook(
        title=(body.title or DEFAULT_NOTEBOOK_TITLE).strip() or DEFAULT_NOTEBOOK_TITLE,
        mode=body.mode or "exploratory",
        class_level=body.class_level,
        subject=body.subject,
        focus=body.focus,
        settings=body.settings,
    )
    return _to_response(notebook)


@router.get("", response_model=NotebookListResponse)
async def list_notebooks(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id, user_id = _get_context(request)
    service = NotebookService(db, tenant_id, user_id)
    notebooks = await service.list_notebooks()
    notebook_ids = [str(nb.id) for nb in notebooks]
    counts_map = await service.get_notebook_list_counts_batch(notebook_ids)
    items = []
    for nb in notebooks:
        counts = counts_map.get(str(nb.id), {
            "sources_count": 0,
            "notes_count": 0,
            "study_assets_count": 0,
            "quizzes_count": 0,
        })
        base = _to_response(nb)
        items.append(NotebookListItemResponse(**base.model_dump(), **counts))
    active = await service.count_active_this_week()
    return NotebookListResponse(notebooks=items, total=len(items), active_this_week=active)


@router.get("/by-slug/{slug}", response_model=NotebookDetailResponse)
async def get_notebook_by_slug(
    slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id, user_id = _get_context(request)
    service = NotebookService(db, tenant_id, user_id)
    notebook = await service.get_notebook_by_slug(slug)
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")
    counts = await service.get_notebook_list_counts(str(notebook.id))
    base = _to_response(notebook)
    settings = notebook.settings if isinstance(notebook.settings, dict) else {}
    return NotebookDetailResponse(**base.model_dump(), **counts, settings=settings)


@router.get("/{notebook_id}", response_model=NotebookDetailResponse)
async def get_notebook(
    notebook_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id, user_id = _get_context(request)
    service = NotebookService(db, tenant_id, user_id)
    notebook = await service.get_notebook(notebook_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")
    counts = await service.get_notebook_list_counts(notebook_id)
    base = _to_response(notebook)
    settings = notebook.settings if isinstance(notebook.settings, dict) else {}
    return NotebookDetailResponse(**base.model_dump(), **counts, settings=settings)


@router.patch("/{notebook_id}", response_model=NotebookResponse)
async def update_notebook(
    notebook_id: str,
    body: NotebookUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id, user_id = _get_context(request)
    service = NotebookService(db, tenant_id, user_id)
    notebook = await service.update_notebook(
        notebook_id,
        title=body.title,
        subtitle=body.subtitle,
        focus=body.focus,
        settings=body.settings,
        touch_last_studied=body.touch_last_studied,
    )
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return _to_response(notebook)


@router.delete("/{notebook_id}")
async def delete_notebook(
    notebook_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id, user_id = _get_context(request)
    service = NotebookService(db, tenant_id, user_id)
    deleted = await service.delete_notebook(notebook_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return {"detail": "Notebook deleted successfully"}
