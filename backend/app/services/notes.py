"""
Notes Service

Handles CRUD operations for notes.
Notes can be manual entries or saved from chat responses.
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.models.note import Note


class NotesService:
    """Service for managing notes."""
    
    def __init__(self, db: AsyncSession, tenant_id: str, user_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
    
    async def create_note(
        self,
        content: str,
        source_ref_id: Optional[str] = None,
    ) -> Note:
        """Create a new note."""
        note = Note(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(self.tenant_id),
            user_id=self.user_id,
            content=content,
            source_ref_id=uuid.UUID(source_ref_id) if source_ref_id else None,
        )
        self.db.add(note)
        await self.db.commit()
        await self.db.refresh(note)
        return note
    
    async def list_notes(self) -> List[Note]:
        """List all notes for user."""
        result = await self.db.execute(
            select(Note).where(
                Note.tenant_id == uuid.UUID(self.tenant_id),
                Note.user_id == self.user_id,
            )
        )
        return result.scalars().all()



