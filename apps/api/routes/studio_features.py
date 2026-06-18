"""Studio features REST API."""

import time

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.schemas.studio_feature import (
    StudioFeatureCreateRequest,
    StudioFeatureListResponse,
    StudioFeatureResponse,
)
from packages.core.database.connection import get_db
from packages.core.services.studio_feature_service import StudioFeatureService
from packages.core.services.notebook_service import NotebookService
from packages.core.services.heatmap_service import update_heatmap_on_quiz

router = APIRouter()


def _get_context(request: Request):
    tenant_id = getattr(request.state, "tenant_id", None)
    user_id = getattr(request.state, "user_id", None)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Tenant context not found")
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")
    return tenant_id, user_id


def _to_response(feature) -> StudioFeatureResponse:
    return StudioFeatureResponse(
        id=str(feature.id),
        notebook_id=str(feature.notebook_id),
        type=feature.type,
        title=feature.title,
        content=feature.content,
        source_ids=feature.source_ids or [],
        created_at=feature.created_at,
        updated_at=feature.updated_at,
    )


@router.get("", response_model=StudioFeatureListResponse)
async def list_studio_features(
    request: Request,
    db: AsyncSession = Depends(get_db),
    notebook_id: str | None = Query(None),
    type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    tenant_id, user_id = _get_context(request)
    service = StudioFeatureService(db, tenant_id, user_id)
    features = await service.get_features(
        limit=limit,
        feature_type=type,
        notebook_id=notebook_id,
    )
    items = [_to_response(f) for f in features]
    return StudioFeatureListResponse(features=items, total=len(items))


@router.get("/{feature_id}", response_model=StudioFeatureResponse)
async def get_studio_feature(
    feature_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id, user_id = _get_context(request)
    service = StudioFeatureService(db, tenant_id, user_id)
    feature = await service.get_feature(feature_id)
    if not feature:
        raise HTTPException(status_code=404, detail="Studio feature not found")
    return _to_response(feature)


@router.post("", response_model=StudioFeatureResponse)
async def create_studio_feature(
    body: StudioFeatureCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id, user_id = _get_context(request)
    t0 = time.perf_counter()
    service = StudioFeatureService(db, tenant_id, user_id)
    feature = await service.save_feature(
        notebook_id=body.notebook_id,
        feature_type=body.type,
        title=body.title,
        content=body.content,
        source_ids=body.source_ids,
    )

    if body.type == "quiz":
        notebook_service = NotebookService(db, tenant_id, user_id)
        notebook = await notebook_service.get_notebook(body.notebook_id)
        if notebook:
            settings = update_heatmap_on_quiz(
                notebook.settings if isinstance(notebook.settings, dict) else {},
                body.content,
            )
            await notebook_service.update_notebook(
                body.notebook_id,
                settings=settings,
                touch_last_studied=True,
            )

    print(
        f"[STUDIO_FEATURES] phase=persist type={body.type} "
        f"ms={int((time.perf_counter() - t0) * 1000)}"
    )
    return _to_response(feature)


@router.delete("/{feature_id}")
async def delete_studio_feature(
    feature_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id, user_id = _get_context(request)
    service = StudioFeatureService(db, tenant_id, user_id)
    deleted = await service.delete_feature(feature_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Studio feature not found")
    return {"detail": "Studio feature deleted successfully"}
