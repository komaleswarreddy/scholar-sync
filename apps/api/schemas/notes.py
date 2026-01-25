"""
Notes Request/Response Schemas

Pydantic models for notes API validation.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class NoteCreateRequest(BaseModel):
    """Request schema for creating a note."""
    content: str = Field(..., min_length=1, description="Note content")
    source_ref_id: Optional[str] = Field(None, description="Optional reference to chat message")


class NoteUpdateRequest(BaseModel):
    """Request schema for updating a note."""
    content: str = Field(..., min_length=1, description="Updated note content")


class NoteResponse(BaseModel):
    """Response schema for a note."""
    id: str
    content: str
    source_ref_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class NoteListResponse(BaseModel):
    """Response schema for note list."""
    notes: list[NoteResponse]


