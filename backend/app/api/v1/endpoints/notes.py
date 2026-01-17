# app/api/v1/endpoints/notes.py
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from pydantic import BaseModel
import uuid

from app.core.database import get_db
from app.services.notes import NotesService

router = APIRouter()

# --- Pydantic Models ---
class NoteRequest(BaseModel):
    content: str
    source_ref_id: Optional[str] = None

class NoteResponse(BaseModel):
    id: str
    content: str

class NotesListResponse(BaseModel):
    notes: List[NoteResponse]

# --- Helper ---
def get_user_tenant(request: Request):
    """Extracts tenant and user context from request state."""
    tenant_id = getattr(request.state, "tenant_id", None)
    user_id = getattr(request.state, "user_id", None)

    if not tenant_id:
        raise HTTPException(status_code=403, detail="Tenant context not found")
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")

    return tenant_id, user_id

# --- Endpoints ---

@router.get("", response_model=NotesListResponse)
async def list_notes(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        tenant_id, user_id = get_user_tenant(request)
        print(f"[NOTES] Listing notes for tenant: {tenant_id}, user: {user_id}")
        service = NotesService(db, tenant_id, user_id)
        notes = await service.list_notes()
        print(f"[NOTES] Found {len(notes)} notes")
        return NotesListResponse(
            notes=[NoteResponse(id=str(n.id), content=n.content) for n in notes]
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"[ERROR] [NOTES] Error listing notes: {type(e).__name__}: {str(e)}")
        print(f"[ERROR] [NOTES] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to list notes: {str(e)}")

@router.post("", response_model=NoteResponse)
async def create_note(
    request_body: NoteRequest, 
    request: Request, 
    db: AsyncSession = Depends(get_db)
):
    tenant_id, user_id = get_user_tenant(request)
    service = NotesService(db, tenant_id, user_id)
    note = await service.create_note(
        content=request_body.content,
        source_ref_id=request_body.source_ref_id,
    )
    return NoteResponse(id=str(note.id), content=note.content)

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
    db: AsyncSession = Depends(get_db)
):
    tenant_id, user_id = get_user_tenant(request)
    service = NotesService(db, tenant_id, user_id)
    note = await service.update_note(note_id, request_body.content)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return NoteResponse(id=str(note.id), content=note.content)

@router.delete("/{note_id}")
async def delete_note(note_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    tenant_id, user_id = get_user_tenant(request)
    service = NotesService(db, tenant_id, user_id)
    if not await service.delete_note(note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    return {"detail": "Note deleted successfully"}