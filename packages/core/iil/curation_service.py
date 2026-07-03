"""Curation review and artifact lifecycle."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.core.database.models.chat import Message
from packages.core.database.models.iil import (
    CurationCandidate,
    DerivedKnowledgeArtifact,
    InteractionFeedback,
    InteractionLog,
)
from packages.core.iil.artifact_extractor import extract_artifact_from_chain
from packages.core.iil.derived_embedder import delete_artifact_embedding, embed_artifact
from packages.core.iil.enums import CurationStatus


async def list_candidates(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    status: Optional[str] = None,
    concept_node_id: Optional[str] = None,
    min_score: Optional[int] = None,
    user_tier: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[List[CurationCandidate], int]:
    q = select(CurationCandidate).where(CurationCandidate.tenant_id == tenant_id)
    if status:
        q = q.where(CurationCandidate.status == status)
    if concept_node_id:
        q = q.where(CurationCandidate.concept_node_id == uuid.UUID(concept_node_id))
    if min_score is not None:
        q = q.where(CurationCandidate.candidate_score >= min_score)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    result = await db.execute(
        q.options(selectinload(CurationCandidate.interaction_log))
        .order_by(CurationCandidate.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    items = list(result.scalars().all())
    if user_tier:
        items = [
            c for c in items
            if c.interaction_log and c.interaction_log.user_tier == user_tier
        ]
    return items, int(total)


async def get_candidate_detail(db: AsyncSession, candidate_id: uuid.UUID) -> Optional[CurationCandidate]:
    result = await db.execute(
        select(CurationCandidate)
        .options(
            selectinload(CurationCandidate.interaction_log),
            selectinload(CurationCandidate.feedback),
            selectinload(CurationCandidate.artifact),
        )
        .where(CurationCandidate.id == candidate_id)
    )
    return result.scalar_one_or_none()


async def _conversation_text_for_log(db: AsyncSession, log: InteractionLog) -> str:
    if not log.message_id:
        return log.query_text or ""
    parts = [f"User: {log.query_text}"]
    msg_result = await db.execute(select(Message).where(Message.id == log.message_id))
    msg = msg_result.scalar_one_or_none()
    if msg:
        parts.append(f"Assistant: {msg.content[:4000]}")
    return "\n\n".join(parts)


async def review_candidate(
    db: AsyncSession,
    *,
    candidate_id: uuid.UUID,
    reviewer_id: str,
    decision: str,
    review_notes: Optional[str] = None,
    confidence_score: Optional[int] = None,
) -> CurationCandidate:
    cand = await get_candidate_detail(db, candidate_id)
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if decision not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="decision must be approved or rejected")

    cand.status = CurationStatus.APPROVED.value if decision == "approved" else CurationStatus.REJECTED.value
    cand.reviewed_by = reviewer_id
    cand.reviewed_at = datetime.now(timezone.utc)
    cand.review_notes = review_notes

    if decision == "approved":
        content = ""
        dimension_tags: List[str] = ["definition"]
        source_ids: List[uuid.UUID] = []

        if cand.source_type == "expert_note" and cand.feedback_id:
            fb_result = await db.execute(
                select(InteractionFeedback).where(InteractionFeedback.id == cand.feedback_id)
            )
            fb = fb_result.scalar_one_or_none()
            content = (fb.free_text if fb else "") or ""
            dimension_tags = ["definition"]
            if fb and fb.dimension_tag:
                dimension_tags = [fb.dimension_tag]
        elif cand.interaction_log:
            content = await _conversation_text_for_log(db, cand.interaction_log)
            extracted = await extract_artifact_from_chain(content)
            content = extracted["content"]
            dimension_tags = extracted.get("dimension_tags") or ["definition"]
            source_ids = [cand.interaction_log.id]

        artifact = DerivedKnowledgeArtifact(
            candidate_id=cand.id,
            concept_node_id=cand.concept_node_id,
            tenant_id=cand.tenant_id,
            dimension_tags=dimension_tags,
            content=content,
            source_interaction_ids=source_ids,
            source_user_tier=cand.interaction_log.user_tier if cand.interaction_log else None,
            confidence_score=confidence_score,
            is_active=True,
        )
        db.add(artifact)
        await db.flush()

        eid = await embed_artifact(
            tenant_id=str(cand.tenant_id),
            artifact_id=str(artifact.id),
            content=content,
            concept_node_id=str(cand.concept_node_id) if cand.concept_node_id else None,
            dimension_tags=dimension_tags,
        )
        if eid:
            artifact.embedding_id = eid

    await db.commit()
    await db.refresh(cand)
    return cand


async def list_artifacts(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    concept_node_id: Optional[str] = None,
    dimension_tag: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[DerivedKnowledgeArtifact]:
    q = select(DerivedKnowledgeArtifact).where(DerivedKnowledgeArtifact.tenant_id == tenant_id)
    if concept_node_id:
        q = q.where(DerivedKnowledgeArtifact.concept_node_id == uuid.UUID(concept_node_id))
    if is_active is not None:
        q = q.where(DerivedKnowledgeArtifact.is_active == is_active)
    if dimension_tag:
        q = q.where(DerivedKnowledgeArtifact.dimension_tags.contains([dimension_tag]))
    result = await db.execute(q.order_by(DerivedKnowledgeArtifact.created_at.desc()).offset(offset).limit(limit))
    return list(result.scalars().all())


async def patch_artifact(
    db: AsyncSession,
    artifact_id: uuid.UUID,
    *,
    is_active: Optional[bool] = None,
    content: Optional[str] = None,
    dimension_tags: Optional[List[str]] = None,
) -> DerivedKnowledgeArtifact:
    result = await db.execute(
        select(DerivedKnowledgeArtifact).where(DerivedKnowledgeArtifact.id == artifact_id)
    )
    art = result.scalar_one_or_none()
    if not art:
        raise HTTPException(status_code=404, detail="Artifact not found")

    if is_active is not None:
        art.is_active = is_active
    if content is not None:
        art.content = content
    if dimension_tags is not None:
        art.dimension_tags = dimension_tags

    if content is not None or dimension_tags is not None:
        if art.embedding_id:
            await delete_artifact_embedding(str(art.tenant_id), art.embedding_id)
        eid = await embed_artifact(
            tenant_id=str(art.tenant_id),
            artifact_id=str(art.id),
            content=art.content,
            concept_node_id=str(art.concept_node_id) if art.concept_node_id else None,
            dimension_tags=list(art.dimension_tags or []),
        )
        art.embedding_id = eid

    await db.commit()
    await db.refresh(art)
    return art


async def coverage_map(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    board: Optional[str] = None,
    class_num: Optional[int] = None,
    subject_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    from packages.core.database.models.concept import Concept

    cq = select(Concept).where(Concept.tenant_id.is_(None))
    if board:
        cq = cq.where(Concept.board == board)
    if class_num is not None:
        cq = cq.where(Concept.class_num == class_num)
    if subject_key:
        cq = cq.where(Concept.subject_key == subject_key)

    concepts = (await db.execute(cq.limit(500))).scalars().all()
    rows: List[Dict[str, Any]] = []
    for c in concepts:
        arts = await db.execute(
            select(DerivedKnowledgeArtifact).where(
                DerivedKnowledgeArtifact.concept_node_id == c.id,
                DerivedKnowledgeArtifact.tenant_id == tenant_id,
                DerivedKnowledgeArtifact.is_active.is_(True),
            )
        )
        dim_counts: Dict[str, int] = {}
        for a in arts.scalars().all():
            for d in a.dimension_tags or []:
                dim_counts[d] = dim_counts.get(d, 0) + 1
        rows.append({
            "concept_id": str(c.id),
            "concept_name": c.name,
            "class_num": c.class_num,
            "subject_key": c.subject_key,
            "chapter_no": c.chapter_no,
            "dimensions": dim_counts,
            "total_artifacts": sum(dim_counts.values()),
        })
    return rows
