from fastapi import APIRouter, UploadFile, File, Form, Depends, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.core.database import get_db, AsyncSessionLocal
from app.services.ingestion import IngestionService
from app.schemas.source import SourceResponse, SourceListResponse

router = APIRouter()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

@router.get("/test")
async def test_endpoint():
    return {"message": "Sources router is working", "status": "ok"}

@router.post("/upload", response_model=SourceResponse)
async def upload_source(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
):
    # 1. Pull validated tenant_id from middleware
    tenant_id = getattr(request.state, "tenant_id", None)
    
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Unauthorized: No valid tenant identified")

    if not file:
        raise HTTPException(status_code=400, detail="File is required")

    # Read content once for validation
    file_content = await file.read()
    file_size = len(file_content)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Max is 10MB.")
    
    if file_size == 0:
        raise HTTPException(status_code=400, detail="File is empty")

    content_type = file.content_type or ""
    
    # Simple type validation
    if content_type not in ["application/pdf", "text/plain"]:
        filename = file.filename or ""
        if not (filename.endswith(".pdf") or filename.endswith(".txt")):
            raise HTTPException(status_code=400, detail="Only PDF and text files supported")
    
    if not title:
        title = file.filename or "Untitled Source"

    try:
        service = IngestionService(db, tenant_id)
        # Use the bytes-direct method because we already read the file
        result = await service.quick_upload_bytes(
            file_content=file_content,
            filename=file.filename or "",
            content_type=content_type,
            title=title
        )

        background_tasks.add_task(process_upload_background, tenant_id, result["id"], content_type)
        return SourceResponse(**result)

    except ValueError as e:
        error_msg = str(e)
        if "not configured" in error_msg.lower():
            raise HTTPException(status_code=503, detail="Storage service not configured.")
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

async def process_upload_background(tenant_id: str, source_id: str, content_type: str):
    """
    Background task to process uploaded file.
    Handles text extraction, chunking, embedding, and vector storage.
    """
    import traceback
    error_occurred = False
    error_message = None
    
    try:
        async with AsyncSessionLocal() as db:
            service = IngestionService(db, tenant_id)
            await service.process_file_background(source_id, content_type)
    except ValueError as e:
        # Expected errors (API keys, configuration, etc.)
        error_message = str(e)
        error_type = type(e).__name__
        full_traceback = traceback.format_exc()
        
        # Log detailed error information
        print(f"[ERROR] Background processing failed for source {source_id}")
        print(f"[ERROR] Error Type: {error_type}")
        print(f"[ERROR] Error Message: {error_message}")
        print(f"[ERROR] Full Traceback:\n{full_traceback}")
        
        # Update source status to ERROR
        from app.models.source import Source, SourceStatus
        from sqlalchemy import select
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Source).where(
                        Source.id == uuid.UUID(source_id),
                        Source.tenant_id == uuid.UUID(tenant_id)
                    )
                )
                source = result.scalar_one_or_none()
                if source:
                    source.status = SourceStatus.ERROR.value
                    source.error_message = error_message
                    await db.commit()
                    print(f"[ERROR] Updated source {source_id} status to ERROR with message: {error_message}")
        except Exception as db_error:
            print(f"[ERROR] Failed to update source status: {db_error}")
            print(traceback.format_exc())
    except Exception as e:
        # Unexpected errors
        error_message = str(e)
        error_type = type(e).__name__
        full_traceback = traceback.format_exc()
        
        # Log detailed error information
        print(f"[ERROR] ⚠️ UNEXPECTED ERROR in background processing for source {source_id}")
        print(f"[ERROR] Error Type: {error_type}")
        print(f"[ERROR] Error Message: {error_message}")
        print(f"[ERROR] Full Traceback:\n{full_traceback}")
        
        # Update source status to ERROR
        from app.models.source import Source, SourceStatus
        from sqlalchemy import select
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Source).where(
                        Source.id == uuid.UUID(source_id),
                        Source.tenant_id == uuid.UUID(tenant_id)
                    )
                )
                source = result.scalar_one_or_none()
                if source:
                    source.status = SourceStatus.ERROR.value
                    source.error_message = error_message
                    await db.commit()
                    print(f"[ERROR] Updated source {source_id} status to ERROR with message: {error_message}")
        except Exception as db_error:
            print(f"[ERROR] Failed to update source status: {db_error}")
            print(traceback.format_exc())

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

    try:
        uuid.UUID(source_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    service = IngestionService(db, tenant_id)
    try:
        await service.delete_source(source_id)
        return JSONResponse(status_code=200, content={"message": "Source deleted"})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))