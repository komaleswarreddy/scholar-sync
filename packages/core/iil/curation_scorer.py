"""Curation candidate scoring engine (spec §4.2)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from packages.core.database.models.iil import (
    CurationCandidate,
    InteractionFeedback,
    InteractionLog,
)
from packages.core.iil.enums import CurationStatus, ExpertiseTier, SignalType

logger = logging.getLogger(__name__)

_TIER_WEIGHTS = {
    ExpertiseTier.SME.value: 3,
    ExpertiseTier.TUTOR.value: 2,
    ExpertiseTier.TEACHER.value: 1,
    ExpertiseTier.STUDENT.value: 0,
}

_HIGH_TIERS = {
    ExpertiseTier.SME.value,
    ExpertiseTier.TUTOR.value,
    ExpertiseTier.TEACHER.value,
}


def compute_score(
    log: Optional[InteractionLog],
    feedback_rows: List[InteractionFeedback],
) -> tuple[int, Dict[str, Any], bool]:
    """Return (score, scoring_signals, hard_reject)."""
    signals: Dict[str, Any] = {}
    score = 0
    hard_reject = False

    if log:
        tw = _TIER_WEIGHTS.get(log.user_tier or "", 0)
        if tw:
            score += tw
            signals["user_tier"] = log.user_tier
        if (log.chain_depth or 0) >= 3:
            score += 2
            signals["chain_depth"] = log.chain_depth

    for fb in feedback_rows:
        if fb.signal_type == SignalType.INACCURATE.value:
            score -= 10
            hard_reject = True
            signals["inaccurate"] = True
        elif fb.signal_type == SignalType.EXPERT_VALIDATED.value:
            score += 4
            signals["expert_validated"] = True
        elif fb.signal_type == SignalType.MISSING_DIMENSION.value and fb.user_tier in _HIGH_TIERS:
            score += 2
            signals["missing_dimension"] = fb.dimension_tag or True
        elif fb.signal_type == SignalType.EXPERT_NOTE.value and fb.user_tier in _HIGH_TIERS:
            score += 4
            signals["expert_note"] = True
        elif fb.signal_type == SignalType.HELPFUL.value and fb.user_tier in _HIGH_TIERS:
            score += 2
            signals["helpful_high_tier"] = True

    return score, signals, hard_reject


async def _is_novel_intent(
    db: AsyncSession,
    log: InteractionLog,
) -> bool:
    if not log.concept_node_id or not log.query_intent:
        return False
    result = await db.execute(
        select(InteractionLog.id).where(
            InteractionLog.concept_node_id == log.concept_node_id,
            InteractionLog.query_intent == log.query_intent,
            InteractionLog.id != log.id,
        ).limit(1)
    )
    return result.scalar_one_or_none() is None


async def score_interaction_log(
    db: AsyncSession,
    log_id: UUID,
    *,
    feedback_id: Optional[UUID] = None,
) -> Optional[CurationCandidate]:
    result = await db.execute(select(InteractionLog).where(InteractionLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        return None

    existing = await db.execute(
        select(CurationCandidate).where(CurationCandidate.interaction_log_id == log_id)
    )
    if existing.scalar_one_or_none():
        return None

    fb_result = await db.execute(
        select(InteractionFeedback).where(InteractionFeedback.message_id == log.message_id)
    )
    feedback_rows = list(fb_result.scalars().all())

    score, signals, hard_reject = compute_score(log, feedback_rows)
    if not hard_reject and await _is_novel_intent(db, log):
        score += 1
        signals["novel_query_angle"] = True

    if hard_reject or score < settings.IIL_CURATION_CANDIDATE_THRESHOLD:
        return None

    cand = CurationCandidate(
        interaction_log_id=log.id,
        feedback_id=feedback_id,
        concept_node_id=log.concept_node_id,
        tenant_id=log.tenant_id,
        source_type="interaction_chain",
        candidate_score=score,
        scoring_signals=signals,
        status=CurationStatus.PENDING.value,
    )
    db.add(cand)
    await db.commit()
    await db.refresh(cand)
    return cand


async def _candidate_from_feedback(
    db: AsyncSession,
    fb: InteractionFeedback,
    *,
    source_type: str,
    signals: Dict[str, Any],
    score: Optional[int] = None,
) -> Optional[CurationCandidate]:
    existing = await db.execute(
        select(CurationCandidate).where(CurationCandidate.feedback_id == fb.id)
    )
    if existing.scalar_one_or_none():
        return None

    cand = CurationCandidate(
        feedback_id=fb.id,
        concept_node_id=fb.concept_node_id,
        tenant_id=fb.tenant_id,
        source_type=source_type,
        candidate_score=score if score is not None else settings.IIL_CURATION_CANDIDATE_THRESHOLD,
        scoring_signals=signals,
        status=CurationStatus.PENDING.value,
    )
    db.add(cand)
    await db.commit()
    await db.refresh(cand)
    return cand


async def score_feedback_event(db: AsyncSession, feedback_id: UUID) -> Optional[CurationCandidate]:
    """Create a curation candidate from an expert feedback event (immediate path)."""
    result = await db.execute(
        select(InteractionFeedback).where(InteractionFeedback.id == feedback_id)
    )
    fb = result.scalar_one_or_none()
    if not fb:
        return None

    # Expert note is content itself — always queue for review.
    if fb.signal_type == SignalType.EXPERT_NOTE.value:
        return await _candidate_from_feedback(
            db,
            fb,
            source_type="expert_note",
            signals={"expert_note": True},
        )

    # Prefer scoring the linked interaction log (has query + chain metadata).
    if fb.message_id:
        log_result = await db.execute(
            select(InteractionLog).where(InteractionLog.message_id == fb.message_id)
        )
        log = log_result.scalar_one_or_none()
        if log:
            cand = await score_interaction_log(db, log.id, feedback_id=fb.id)
            if cand:
                return cand

    # Fallback when log is missing or score below threshold but signal is strong.
    if fb.signal_type == SignalType.EXPERT_VALIDATED.value:
        return await _candidate_from_feedback(
            db,
            fb,
            source_type="expert_validated",
            signals={"expert_validated": True, "fallback": True},
            score=settings.IIL_CURATION_CANDIDATE_THRESHOLD,
        )

    if fb.signal_type == SignalType.MISSING_DIMENSION.value:
        return await _candidate_from_feedback(
            db,
            fb,
            source_type="missing_dimension",
            signals={"missing_dimension": fb.dimension_tag or True, "fallback": True},
            score=settings.IIL_CURATION_CANDIDATE_THRESHOLD,
        )

    return None


# Back-compat alias
async def score_expert_note_feedback(db: AsyncSession, feedback_id: UUID) -> Optional[CurationCandidate]:
    return await score_feedback_event(db, feedback_id)


async def run_scoring_batch(db: AsyncSession, *, limit: int = 100) -> int:
    """Scan recent logs without candidates and score them."""
    subq = select(CurationCandidate.interaction_log_id).where(
        CurationCandidate.interaction_log_id.isnot(None)
    )
    result = await db.execute(
        select(InteractionLog)
        .where(InteractionLog.id.notin_(subq))
        .order_by(InteractionLog.created_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    created = 0
    for log in logs:
        if await score_interaction_log(db, log.id):
            created += 1
    return created
