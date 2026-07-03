"""Message feedback API — tiered IIL signals."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.routes.admin import check_admin_role
from config.settings import settings
from packages.core.database.connection import get_db
from packages.core.iil.feedback_service import delete_feedback, list_feedback_for_message, submit_feedback
from packages.core.iil.scheduler import trigger_scoring_on_feedback

router = APIRouter()


class FeedbackCreateRequest(BaseModel):
    signal_type: str
    dimension_tag: Optional[str] = None
    free_text: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: str
    message_id: Optional[str] = None
    user_id: str
    user_tier: str
    signal_type: str
    concept_node_id: Optional[str] = None
    dimension_tag: Optional[str] = None
    free_text: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


def _to_response(fb) -> FeedbackResponse:
    return FeedbackResponse(
        id=str(fb.id),
        message_id=str(fb.message_id) if fb.message_id else None,
        user_id=fb.user_id,
        user_tier=fb.user_tier,
        signal_type=fb.signal_type,
        concept_node_id=str(fb.concept_node_id) if fb.concept_node_id else None,
        dimension_tag=fb.dimension_tag,
        free_text=fb.free_text,
        created_at=fb.created_at.isoformat() if fb.created_at else None,
    )


@router.post("/messages/{message_id}/feedback", response_model=FeedbackResponse, status_code=201)
async def create_message_feedback(
    message_id: str,
    body: FeedbackCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id = getattr(request.state, "tenant_id", None)
    user_id = getattr(request.state, "user_id", None)
    if not tenant_id or not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    fb = await submit_feedback(
        db,
        message_id=message_id,
        tenant_id=str(tenant_id),
        user_id=str(user_id),
        signal_type=body.signal_type,
        dimension_tag=body.dimension_tag,
        free_text=body.free_text,
    )
    if body.signal_type in ("expert_note", "expert_validated"):
        trigger_scoring_on_feedback(str(fb.id))
    return _to_response(fb)


@router.get("/messages/{message_id}/feedback", response_model=List[FeedbackResponse])
async def get_message_feedback(
    message_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id = getattr(request.state, "tenant_id", None)
    user_id = getattr(request.state, "user_id", None)
    if not tenant_id or not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    is_admin = await check_admin_role(request, db, raise_on_db_unavailable=False)
    rows = await list_feedback_for_message(
        db,
        message_id=message_id,
        tenant_id=str(tenant_id),
        user_id=str(user_id),
        is_admin=is_admin,
    )
    return [_to_response(r) for r in rows]


@router.delete("/messages/{message_id}/feedback/{feedback_id}", status_code=204)
async def remove_message_feedback(
    message_id: str,
    feedback_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id = getattr(request.state, "tenant_id", None)
    user_id = getattr(request.state, "user_id", None)
    if not tenant_id or not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    await delete_feedback(
        db,
        message_id=message_id,
        feedback_id=feedback_id,
        tenant_id=str(tenant_id),
        user_id=str(user_id),
    )
