"""Background IIL jobs — scoring interval + template extraction."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from config.settings import settings
from packages.core.database.connection import AsyncSessionLocal
from packages.core.iil.curation_scorer import run_scoring_batch

logger = logging.getLogger(__name__)

_scheduler_task: Optional[asyncio.Task] = None


async def _scoring_loop() -> None:
    interval = max(60, settings.IIL_CURATION_SCORING_INTERVAL_MINUTES * 60)
    while True:
        try:
            if settings.IIL_ENABLED:
                async with AsyncSessionLocal() as db:
                    n = await run_scoring_batch(db)
                    if n:
                        logger.info("IIL scoring batch: %d new candidate(s)", n)
                await _extract_exploration_templates()
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("IIL scoring loop error: %s", exc)
        await asyncio.sleep(interval)


async def _extract_exploration_templates() -> None:
    """P2: extract templates from deep tutor/SME chains."""
    from sqlalchemy import select

    from packages.core.database.models.iil import ExplorationTemplate, InteractionLog
    from packages.core.iil.enums import ExpertiseTier

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(InteractionLog)
            .where(InteractionLog.user_tier.in_([ExpertiseTier.TUTOR.value, ExpertiseTier.SME.value]))
            .where(InteractionLog.chain_depth >= 3)
            .where(InteractionLog.concept_node_id.isnot(None))
            .order_by(InteractionLog.created_at.desc())
            .limit(20)
        )
        logs = result.scalars().all()
        for log in logs:
            if not log.concept_node_id:
                continue
            existing = await db.execute(
                select(ExplorationTemplate).where(
                    ExplorationTemplate.concept_node_id == log.concept_node_id,
                    ExplorationTemplate.tenant_id == log.tenant_id,
                ).limit(1)
            )
            if existing.scalar_one_or_none():
                continue
            tpl = ExplorationTemplate(
                concept_node_id=log.concept_node_id,
                tenant_id=log.tenant_id,
                source_chain_ids=[log.id],
                source_user_tier=log.user_tier,
                dimension_sequence=["definition", "intuition"],
                template_prompts=[
                    {
                        "prompt_text": f"Explore {log.query_text[:120]} in more depth",
                        "target_dimension": "intuition",
                        "personalization_hint": log.user_tier,
                    }
                ],
                is_active=True,
            )
            db.add(tpl)
        await db.commit()


async def trigger_scoring_on_feedback(feedback_id: str) -> None:
    """Event-driven scoring for expert notes."""
    from uuid import UUID

    from packages.core.iil.curation_scorer import score_expert_note_feedback

    try:
        async with AsyncSessionLocal() as db:
            await score_expert_note_feedback(db, UUID(feedback_id))
    except Exception as exc:
        logger.error("IIL feedback scoring failed: %s", exc)


def start_iil_scheduler() -> None:
    global _scheduler_task
    if not settings.IIL_ENABLED:
        return
    if _scheduler_task and not _scheduler_task.done():
        return
    try:
        loop = asyncio.get_running_loop()
        _scheduler_task = loop.create_task(_scoring_loop())
        logger.info("IIL scheduler started (interval %dm)", settings.IIL_CURATION_SCORING_INTERVAL_MINUTES)
    except RuntimeError:
        pass


async def stop_iil_scheduler() -> None:
    global _scheduler_task
    if _scheduler_task:
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
        _scheduler_task = None
