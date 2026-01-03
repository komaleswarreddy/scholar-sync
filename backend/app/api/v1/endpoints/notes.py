"""
Notes API Endpoints

Handles saving and retrieving notes (manual entries or saved chat responses).
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.core.config import settings
from app.services.notes import NotesService

router = APIRouter()


class NoteRequest(BaseModel):
    """Request schema for creating note."""
    content: str
    source_ref_id: Optional[str] = None  # Optional link to chat message


@router.post("/")
async def create_note(
    request_body: NoteRequest,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new note.
    
    Can be:
    - Manual entry (content only)
    - Saved from chat (with source_ref_id)
    """
    tenant_id = request.state.tenant_id
    user_id = request.headers.get("X-User-ID")
    
    # For development: use default user if not provided
    if not user_id:
        if settings.ENVIRONMENT == "development":
            user_id = "dev-user-123"
        else:
            raise HTTPException(status_code=401, detail="User ID required")
    
    service = NotesService(db, tenant_id, user_id)
    note = await service.create_note(
        content=request_body.content,
        source_ref_id=request_body.source_ref_id,
    )
    
    return JSONResponse(content={"id": str(note.id), "content": note.content})


@router.get("/")
async def list_notes(
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get all notes for the current user.
    """
    tenant_id = request.state.tenant_id
    user_id = request.headers.get("X-User-ID")
    
    # For development: use default user if not provided
    if not user_id:
        if settings.ENVIRONMENT == "development":
            user_id = "dev-user-123"
        else:
            raise HTTPException(status_code=401, detail="User ID required")
    
    service = NotesService(db, tenant_id, user_id)
    notes = await service.list_notes()
    
    return JSONResponse(content={"notes": [{"id": str(n.id), "content": n.content} for n in notes]})

