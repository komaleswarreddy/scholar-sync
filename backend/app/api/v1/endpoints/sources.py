from fastapi import APIRouter, UploadFile, File, Depends, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.core.database import get_db, AsyncSessionLocal
from app.services.ingestion import IngestionService
from app.schemas.source import SourceResponse, SourceListResponse

router = APIRouter()

@router.post("/upload", response_model=SourceResponse)
async def upload_source(
    file: UploadFile = File(...),
    title: str = None,
    request: Request = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
):
    # 1. Pull validated tenant_id from middleware
    tenant_id = getattr(request.state, "tenant_id", None)
    
    # 2. Handle invalid/non-existent tenant gracefully (Task B.b & B.c)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Unauthorized: No valid tenant identified")

    if not file:
        raise HTTPException(status_code=400, detail="File is required")

    content_type = file.content_type or ""
    if content_type not in ["application/pdf", "text/plain"]:
        filename = file.filename or ""
        if not (filename.endswith(".pdf") or filename.endswith(".txt")):
            raise HTTPException(status_code=400, detail="Only PDF and text files are supported")

    if not title:
        title = file.filename or "Untitled Source"

    # 3. Ensure Service receives the tenant_id
    service = IngestionService(db, tenant_id)
    result = await service.quick_upload(file, title)

    background_tasks.add_task(process_upload_background, tenant_id, result["id"], content_type)
    return SourceResponse(**result)

async def process_upload_background(tenant_id: str, source_id: str, content_type: str):
    """
    Background task also needs the tenant_id to maintain isolation.
    """
    try:
        async with AsyncSessionLocal() as db:
            service = IngestionService(db, tenant_id)
            await service.process_file_background(source_id, content_type)
    except Exception as e:
        import traceback
        print(f"Background Process Error for Tenant {tenant_id}: {traceback.format_exc()}")
        from app.models.source import Source, SourceStatus
        from sqlalchemy import select
        async with AsyncSessionLocal() as db:
            # Important: Filter by tenant_id even in error handling for safety
            result = await db.execute(
                select(Source).where(
                    Source.id == uuid.UUID(source_id),
                    Source.tenant_id == uuid.UUID(tenant_id) # Safety check
                )
            )
            source = result.scalar_one_or_none()
            if source:
                source.status = SourceStatus.ERROR.value
                await db.commit()

@router.get("/sources", response_model=SourceListResponse)
async def list_sources(request: Request, db: AsyncSession = Depends(get_db)):
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Tenant identification failed")

    service = IngestionService(db, tenant_id)
    sources = await service.list_sources()
    return SourceListResponse(sources=sources)

@router.delete("/sources/{source_id}")
async def delete_source(source_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Tenant identification failed")

    service = IngestionService(db, tenant_id)
    await service.delete_source(source_id)
    return JSONResponse(status_code=200, content={"message": "Source deleted"})