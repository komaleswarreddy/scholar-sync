"""Proactive response enrichment from derived artifacts (spec §5.4)."""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from packages.core.database.models.iil import DerivedKnowledgeArtifact, InteractionFeedback
from packages.core.iil.enums import SignalType


async def build_enrichment_block(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    concept_node_id: Optional[UUID],
) -> str:
    """Return system-prompt supplement from active derived artifacts (max N dimensions)."""
    if not concept_node_id or not settings.IIL_ENABLED:
        return ""

    off_syllabus_logs = select(InteractionFeedback.message_id).where(
        InteractionFeedback.signal_type == SignalType.OFF_SYLLABUS.value,
        InteractionFeedback.tenant_id == tenant_id,
    )

    result = await db.execute(
        select(DerivedKnowledgeArtifact)
        .where(
            DerivedKnowledgeArtifact.tenant_id == tenant_id,
            DerivedKnowledgeArtifact.concept_node_id == concept_node_id,
            DerivedKnowledgeArtifact.is_active.is_(True),
        )
        .limit(settings.IIL_ENRICHMENT_MAX_DIMENSIONS * 2)
    )
    artifacts = result.scalars().all()
    if len(artifacts) < 2:
        return ""

    lines: List[str] = ["Additional expert-curated dimensions (supplementary only):"]
    seen_dims: set[str] = set()
    for art in artifacts:
        for dim in art.dimension_tags or []:
            if dim in seen_dims:
                continue
            seen_dims.add(dim)
            lines.append(f"- [{dim}] {art.content[:400]}...")
            if len(seen_dims) >= settings.IIL_ENRICHMENT_MAX_DIMENSIONS:
                break
        if len(seen_dims) >= settings.IIL_ENRICHMENT_MAX_DIMENSIONS:
            break

    return "\n".join(lines) if len(seen_dims) >= 2 else ""


async def get_template_prompts_for_concept(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    concept_node_id: Optional[UUID],
    limit: int = 3,
) -> List[str]:
    """P2: starter prompts from ExplorationTemplate."""
    if not concept_node_id:
        return []
    from packages.core.database.models.iil import ExplorationTemplate

    result = await db.execute(
        select(ExplorationTemplate)
        .where(
            ExplorationTemplate.tenant_id == tenant_id,
            ExplorationTemplate.concept_node_id == concept_node_id,
            ExplorationTemplate.is_active.is_(True),
        )
        .limit(limit)
    )
    prompts: List[str] = []
    for tpl in result.scalars().all():
        for p in tpl.template_prompts or []:
            if isinstance(p, dict) and p.get("prompt_text"):
                prompts.append(str(p["prompt_text"]))
    return prompts[:limit]
