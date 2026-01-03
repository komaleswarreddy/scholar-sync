"""
Source Management API Endpoints

Handles file upload, text extraction, chunking, and vector indexing.
All operations are tenant-scoped via middleware.
"""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import uuid

from app.core.database import get_db, AsyncSessionLocal
from app.schemas.source import SourceResponse, SourceListResponse
from app.services.ingestion import IngestionService

router = APIRouter()


@router.post("/upload", response_model=SourceResponse)
async def upload_source(
    file: UploadFile = File(...),
    title: str = None,
    request: Request = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a source file (PDF or text).
    
    Returns immediately with "processing" status.
    File processing happens in background.
    
    Process:
    1. Validate file type
    2. Save file to storage
    3. Create database record with "processing" status
    4. Return immediately
    5. Background: Extract, chunk, embed, index
    """
    try:
        tenant_id = request.state.tenant_id
        
        if not file:
            raise HTTPException(status_code=400, detail="File is required")
        
        # Validate file type
        content_type = file.content_type or ""
        if content_type not in ["application/pdf", "text/plain"]:
            # Also check filename extension as fallback
            filename = file.filename or ""
            if not (filename.endswith(".pdf") or filename.endswith(".txt")):
                raise HTTPException(
                    status_code=400,
                    detail="Only PDF and text files are supported"
                )
        
        # Use filename as title if not provided
        if not title:
            title = file.filename or "Untitled Source"
        
        # Quick upload: Save file and create record, return immediately
        service = IngestionService(db, tenant_id)
        result = await service.quick_upload(file, title)
        
        # Process in background (pass source_id, background task will read from storage)
        background_tasks.add_task(
            process_upload_background,
            tenant_id=tenant_id,
            source_id=result["id"],
            content_type=content_type,
        )
        
        # Remove file_content from response (not needed)
        result.pop("file_content", None)
        return SourceResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"❌ Upload error: {type(e).__name__}: {str(e)}")
        print(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )


async def process_upload_background(
    tenant_id: str,
    source_id: str,
    content_type: str,
):
    """Background task to process uploaded file."""
    try:
        async with AsyncSessionLocal() as db:
            service = IngestionService(db, tenant_id)
            await service.process_file_background(
                source_id=source_id,
                content_type=content_type,
            )
    except Exception as e:
        import traceback
        print(f"❌ Background processing error for {source_id}: {type(e).__name__}: {str(e)}")
        print(f"❌ Traceback: {traceback.format_exc()}")
        # Update status to error in database
        async with AsyncSessionLocal() as db:
            from app.models.source import Source, SourceStatus
            from sqlalchemy import select
            result = await db.execute(select(Source).where(Source.id == uuid.UUID(source_id)))
            source = result.scalar_one_or_none()
            if source:
                source.status = SourceStatus.ERROR.value  # Store enum value as string
                await db.commit()


@router.get("/sources", response_model=SourceListResponse)
async def list_sources(
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get all sources for the current tenant.
    
    Returns:
        List of sources with metadata
    """
    tenant_id = request.state.tenant_id
    
    service = IngestionService(db, tenant_id)
    sources = await service.list_sources()
    
    return SourceListResponse(sources=sources)


@router.delete("/sources/{source_id}")
async def delete_source(
    source_id: str,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a source and all associated vectors.
    
    Process:
    1. Delete vectors from Pinecone (tenant namespace)
    2. Delete file from S3
    3. Delete record from database
    """
    tenant_id = request.state.tenant_id
    
    service = IngestionService(db, tenant_id)
    await service.delete_source(source_id)
    
    return JSONResponse(status_code=200, content={"message": "Source deleted"})

