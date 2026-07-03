"""Home dashboard summary API."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import uuid

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
    if focus and settings.IIL_ENABLED:
        try:
            concept_id = await map_concept_from_query(db, focus.get("topic") or "")
            if concept_id:
                prompts = await get_template_prompts_for_concept(
                    db,
                    tenant_id=uuid.UUID(tenant_id),
                    concept_node_id=concept_id,
                    limit=3,
                )
                if prompts:
                    focus["starter_prompts"] = prompts
                    data["focus_concept"] = focus
        except Exception:
            pass
    return HomeSummaryResponse(**data)
