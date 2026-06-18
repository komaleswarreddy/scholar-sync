"""Home dashboard summary API."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.schemas.home import HomeSummaryResponse
from packages.core.database.connection import get_db
from packages.core.services.home_summary_service import HomeSummaryService

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
    return HomeSummaryResponse(**data)
