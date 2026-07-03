"""Platform admin curation API (spec §4.7)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.routes.admin import check_admin_role
from packages.core.database.connection import get_db
from packages.core.iil import curation_service

router = APIRouter()


class ReviewRequest(BaseModel):
    decision: str = Field(..., pattern="^(approved|rejected)$")
    review_notes: Optional[str] = None
    confidence_score: Optional[int] = Field(default=None, ge=1, le=5)


class PatchArtifactRequest(BaseModel):
    is_active: Optional[bool] = None
    content: Optional[str] = None
    dimension_tags: Optional[List[str]] = None


async def _require_platform_admin(request: Request, db: AsyncSession) -> None:
    ok = await check_admin_role(request, db, raise_on_db_unavailable=True)
    if not ok:
        raise HTTPException(status_code=403, detail="Platform admin required")


@router.get("/curation/candidates")
async def list_curation_candidates(
    request: Request,
    db: AsyncSession = Depends(get_db),
    status: Optional[str] = None,
    concept_node_id: Optional[str] = None,
    min_score: Optional[int] = None,
    user_tier: Optional[str] = None,
    limit: int = Query(50, le=100),
    offset: int = 0,
):
    await _require_platform_admin(request, db)
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant required")
    import uuid

    items, total = await curation_service.list_candidates(
        db, uuid.UUID(str(tenant_id)),
        status=status, concept_node_id=concept_node_id,
        min_score=min_score, user_tier=user_tier, limit=limit, offset=offset,
    )
    return {
        "items": [
            {
                "id": str(c.id),
                "status": c.status,
                "candidate_score": c.candidate_score,
                "source_type": c.source_type,
                "concept_node_id": str(c.concept_node_id) if c.concept_node_id else None,
                "scoring_signals": c.scoring_signals,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in items
        ],
        "total": total,
    }


@router.get("/curation/candidates/{candidate_id}")
async def get_curation_candidate(
    candidate_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await _require_platform_admin(request, db)
    import uuid

    cand = await curation_service.get_candidate_detail(db, uuid.UUID(candidate_id))
    if not cand:
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "id": str(cand.id),
        "status": cand.status,
        "candidate_score": cand.candidate_score,
        "scoring_signals": cand.scoring_signals,
        "interaction_log": {
            "id": str(cand.interaction_log.id),
            "query_text": cand.interaction_log.query_text,
            "chain_depth": cand.interaction_log.chain_depth,
            "user_tier": cand.interaction_log.user_tier,
        } if cand.interaction_log else None,
        "feedback": {
            "id": str(cand.feedback.id),
            "signal_type": cand.feedback.signal_type,
            "free_text": cand.feedback.free_text,
        } if cand.feedback else None,
        "artifact_preview": cand.artifact.content[:500] if cand.artifact else None,
    }


@router.post("/curation/candidates/{candidate_id}/review")
async def review_curation_candidate(
    candidate_id: str,
    body: ReviewRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await _require_platform_admin(request, db)
    user_id = getattr(request.state, "user_id", None)
    import uuid

    cand = await curation_service.review_candidate(
        db,
        candidate_id=uuid.UUID(candidate_id),
        reviewer_id=str(user_id),
        decision=body.decision,
        review_notes=body.review_notes,
        confidence_score=body.confidence_score,
    )
    return {"id": str(cand.id), "status": cand.status}


@router.get("/curation/coverage-map")
async def get_coverage_map(
    request: Request,
    db: AsyncSession = Depends(get_db),
    board: Optional[str] = None,
    class_num: Optional[int] = None,
    subject_key: Optional[str] = None,
):
    await _require_platform_admin(request, db)
    tenant_id = getattr(request.state, "tenant_id", None)
    import uuid

    rows = await curation_service.coverage_map(
        db, uuid.UUID(str(tenant_id)),
        board=board, class_num=class_num, subject_key=subject_key,
    )
    return {"rows": rows}


@router.get("/curation/artifacts")
async def list_curation_artifacts(
    request: Request,
    db: AsyncSession = Depends(get_db),
    concept_node_id: Optional[str] = None,
    dimension_tag: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = Query(50, le=100),
    offset: int = 0,
):
    await _require_platform_admin(request, db)
    tenant_id = getattr(request.state, "tenant_id", None)
    import uuid

    arts = await curation_service.list_artifacts(
        db, uuid.UUID(str(tenant_id)),
        concept_node_id=concept_node_id, dimension_tag=dimension_tag,
        is_active=is_active, limit=limit, offset=offset,
    )
    return {
        "items": [
            {
                "id": str(a.id),
                "concept_node_id": str(a.concept_node_id) if a.concept_node_id else None,
                "dimension_tags": a.dimension_tags,
                "content": a.content[:300],
                "confidence_score": a.confidence_score,
                "is_active": a.is_active,
            }
            for a in arts
        ]
    }


@router.patch("/curation/artifacts/{artifact_id}")
async def patch_curation_artifact(
    artifact_id: str,
    body: PatchArtifactRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await _require_platform_admin(request, db)
    import uuid

    art = await curation_service.patch_artifact(
        db, uuid.UUID(artifact_id),
        is_active=body.is_active, content=body.content, dimension_tags=body.dimension_tags,
    )
    return {"id": str(art.id), "is_active": art.is_active}
