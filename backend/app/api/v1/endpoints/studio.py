# app/api/v1/endpoints/studio.py

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.studio import StudioService
from app.schemas.studio import StudioRequest

router = APIRouter()

@router.post("/generate")
async def generate_studio_content(
    request_body: StudioRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id = request.state.tenant_id
    service = StudioService(db, tenant_id)

    result = await service.generate(
        task_type=request_body.task_type,
        source_ids=request_body.source_ids,
        custom_instructions=request_body.custom_instructions,
    )

    return JSONResponse(content=result)
