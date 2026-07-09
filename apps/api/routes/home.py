"""Home dashboard summary API."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import asyncio

from apps.api.schemas.home import HomeSummaryResponse
from config.settings import settings
from packages.core.database.connection import get_db
from packages.core.services.home_summary_service import HomeSummaryService
from packages.core.iil.concept_mapper import map_concept_from_query
from packages.core.iil.enrichment import get_template_prompts_for_concept

router = APIRouter()


def _get_context(request: Request):
    tenant_id = getattr(request.state, "tenant_id", None)
    user_id = getattr(request.state, "user_id", None)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Tenant context not found")
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")
    return tenant_id, user_id


@router.get("/summary", response_model=HomeSummaryResponse)
async def get_home_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id, user_id = _get_context(request)
    service = HomeSummaryService(db, tenant_id, user_id)
    data = await service.get_summary()
    focus = data.get("focus_concept")
    topic = (focus.get("topic") or "") if focus else ""
    if focus and settings.IIL_ENABLED and len(topic.strip()) >= 6:
        try:
            # Both steps are sequential by necessity (the second needs the first's
            # concept_id), but they're bounded by ONE shared timeout budget instead
            # of two stacked 1.5s timeouts — caps worst-case added latency on the
            # home page's critical path at ~1.5s instead of ~3s.
            async def _enrich_with_starter_prompts():
                concept_id = await map_concept_from_query(db, topic)
                if not concept_id:
                    return None
                return await get_template_prompts_for_concept(
                    db,
                    tenant_id=uuid.UUID(tenant_id),
                    concept_node_id=concept_id,
                    limit=3,
                )

            prompts = await asyncio.wait_for(_enrich_with_starter_prompts(), timeout=1.5)
            if prompts:
                focus["starter_prompts"] = prompts
                data["focus_concept"] = focus
        except Exception:
            pass
    return HomeSummaryResponse(**data)
