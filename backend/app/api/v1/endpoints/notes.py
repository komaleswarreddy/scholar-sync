# app/api/v1/endpoints/notes.py
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from pydantic import BaseModel
import uuid

from app.core.database import get_db
from app.services.notes import NotesService

router = APIRouter()

# ---------------------------
# Pydantic Models
# ---------------------------
class NoteRequest(BaseModel):
    content: str
    source_ref_id: Optional[str] = None

class NoteResponse(BaseModel):
    id: str
    content: str

class NotesListResponse(BaseModel):
    notes: List[NoteResponse]

# ---------------------------
# Helper to get user and tenant
# ---------------------------
def get_user_tenant(request: Request):
    """
    Returns tenant_id and user_id from middleware.
    Supports X-User-ID header override.
    Raises 401 if user_id is missing.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    # Check X-User-ID header first, fallback to middleware user_id
    user_id = request.headers.get("X-User-ID") or getattr(request.state, "user_id", None)

    if not tenant_id:
        raise HTTPException(status_code=500, detail="Tenant not set in request state")
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")

    return tenant_id, user_id

# ---------------------------
# Endpoints
# ---------------------------

@router.post("", response_model=NoteResponse)
async def create_note(
    request_body: NoteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id, user_id = get_user_tenant(request)
    service = NotesService(db, tenant_id, user_id)
    note = await service.create_note(
        content=request_body.content,
        source_ref_id=request_body.source_ref_id,
    )
    return NoteResponse(id=str(note.id), content=note.content)

@router.get("", response_model=NotesListResponse)
async def list_notes(request: Request, db: AsyncSession = Depends(get_db)):
    tenant_id, user_id = get_user_tenant(request)
    service = NotesService(db, tenant_id, user_id)
    notes = await service.list_notes()
    return NotesListResponse(
        notes=[NoteResponse(id=str(n.id), content=n.content) for n in notes]
    )

@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(note_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    tenant_id, user_id = get_user_tenant(request)
    service = NotesService(db, tenant_id, user_id)
    note = await service.get_note_by_id(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return NoteResponse(id=str(note.id), content=note.content)

@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: str,
    request_body: NoteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id, user_id = get_user_tenant(request)
    service = NotesService(db, tenant_id, user_id)
    note = await service.update_note(note_id, request_body.content)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return NoteResponse(id=str(note.id), content=note.content)

@router.delete("/{note_id}", response_model=dict)
async def delete_note(note_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    tenant_id, user_id = get_user_tenant(request)
    service = NotesService(db, tenant_id, user_id)
    success = await service.delete_note(note_id)
    if not success:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"detail": "Note deleted successfully"}
