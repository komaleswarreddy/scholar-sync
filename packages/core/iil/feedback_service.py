"""InteractionFeedback CRUD with tier validation."""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.database.models.chat import Chat, Message
from packages.core.database.models.iil import InteractionFeedback, InteractionLog
from packages.core.database.models.user import User
from packages.core.iil.enums import (
    DimensionTag,
    SignalType,
    TIER1_SIGNALS,
    default_expertise_tier_for_role,
    tier_allows_signal,
)


async def _get_user_tier(db: AsyncSession, user_id: str) -> str:
    try:
        uid = uuid.UUID(user_id)
        result = await db.execute(select(User).where(User.id == uid))
    except ValueError:
        result = await db.execute(select(User).where(User.clerk_user_id == user_id).limit(1))
    user = result.scalar_one_or_none()
    if user and user.expertise_tier:
        return user.expertise_tier
    if user:
        return default_expertise_tier_for_role(user.role)
    return "student"


async def _verify_message_access(
    db: AsyncSession,
    message_id: uuid.UUID,
    tenant_id: uuid.UUID,
    user_id: str,
    *,
    admin_view: bool = False,
) -> Message:
    result = await db.execute(
        select(Message)
        .join(Chat)
        .where(Message.id == message_id)
        .where(Chat.tenant_id == tenant_id)
    )
    message = result.scalar_one_or_none()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    if not admin_view:
        chat_result = await db.execute(select(Chat).where(Chat.id == message.chat_id))
        chat = chat_result.scalar_one_or_none()
        if chat and chat.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
    return message


def _validate_signal_payload(signal_type: str, dimension_tag: Optional[str], free_text: Optional[str]) -> None:
    try:
        sig = SignalType(signal_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid signal_type: {signal_type}")

    if sig == SignalType.INACCURATE and not (free_text or "").strip():
        raise HTTPException(status_code=400, detail="free_text required for inaccurate")
    if sig == SignalType.EXPERT_NOTE and not (free_text or "").strip():
        raise HTTPException(status_code=400, detail="free_text required for expert_note")
    if sig == SignalType.MISSING_DIMENSION:
        if not dimension_tag:
            raise HTTPException(status_code=400, detail="dimension_tag required for missing_dimension")
        try:
            DimensionTag(dimension_tag)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid dimension_tag: {dimension_tag}")


async def submit_feedback(
    db: AsyncSession,
    *,
    message_id: str,
    tenant_id: str,
    user_id: str,
    signal_type: str,
    dimension_tag: Optional[str] = None,
    free_text: Optional[str] = None,
) -> InteractionFeedback:
    msg_uuid = uuid.UUID(message_id)
    tenant_uuid = uuid.UUID(tenant_id)
    await _verify_message_access(db, msg_uuid, tenant_uuid, user_id)

    user_tier = await _get_user_tier(db, user_id)
    if not tier_allows_signal(user_tier, signal_type):
        raise HTTPException(status_code=403, detail="Insufficient expertise tier for this signal")

    _validate_signal_payload(signal_type, dimension_tag, free_text)

    try:
        sig = SignalType(signal_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid signal_type")

    # Tier 1: mutually exclusive — remove other tier1 signals from same user
    if sig in TIER1_SIGNALS:
        existing = await db.execute(
            select(InteractionFeedback).where(
                InteractionFeedback.message_id == msg_uuid,
                InteractionFeedback.user_id == user_id,
                InteractionFeedback.signal_type.in_([s.value for s in TIER1_SIGNALS]),
            )
        )
        for row in existing.scalars().all():
            await db.delete(row)

    concept_node_id = None
    log_result = await db.execute(
        select(InteractionLog).where(InteractionLog.message_id == msg_uuid)
    )
    log = log_result.scalar_one_or_none()
    if log and log.concept_node_id:
        concept_node_id = log.concept_node_id

    fb = InteractionFeedback(
        message_id=msg_uuid,
        user_id=user_id,
        user_tier=user_tier,
        signal_type=signal_type,
        concept_node_id=concept_node_id,
        dimension_tag=dimension_tag,
        free_text=(free_text or "").strip() or None,
        tenant_id=tenant_uuid,
    )
    db.add(fb)
    await db.commit()
    await db.refresh(fb)
    return fb


async def list_feedback_for_message(
    db: AsyncSession,
    *,
    message_id: str,
    tenant_id: str,
    user_id: str,
    is_admin: bool,
) -> List[InteractionFeedback]:
    msg_uuid = uuid.UUID(message_id)
    tenant_uuid = uuid.UUID(tenant_id)
    await _verify_message_access(db, msg_uuid, tenant_uuid, user_id, admin_view=is_admin)

    q = select(InteractionFeedback).where(
        InteractionFeedback.message_id == msg_uuid,
        InteractionFeedback.tenant_id == tenant_uuid,
    )
    if not is_admin:
        q = q.where(InteractionFeedback.user_id == user_id)
    result = await db.execute(q.order_by(InteractionFeedback.created_at.asc()))
    return list(result.scalars().all())


async def delete_feedback(
    db: AsyncSession,
    *,
    message_id: str,
    feedback_id: str,
    tenant_id: str,
    user_id: str,
) -> None:
    msg_uuid = uuid.UUID(message_id)
    fb_uuid = uuid.UUID(feedback_id)
    tenant_uuid = uuid.UUID(tenant_id)

    result = await db.execute(
        select(InteractionFeedback).where(
            InteractionFeedback.id == fb_uuid,
            InteractionFeedback.message_id == msg_uuid,
            InteractionFeedback.tenant_id == tenant_uuid,
            InteractionFeedback.user_id == user_id,
        )
    )
    fb = result.scalar_one_or_none()
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback not found")
    await db.delete(fb)
    await db.commit()
