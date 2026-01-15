# app/services/notes.py
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from app.models.note import Note

class NotesService:
    def __init__(self, db: AsyncSession, tenant_id: str, user_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    async def create_note(self, content: str, source_ref_id: Optional[str] = None) -> Note:
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
        result = await self.db.execute(
            select(Note).where(
                Note.tenant_id == uuid.UUID(self.tenant_id),
                Note.user_id == self.user_id,
            )
        )
        return result.scalars().all()

    async def get_note_by_id(self, note_id: str) -> Optional[Note]:
        result = await self.db.execute(
            select(Note).where(
                Note.id == uuid.UUID(note_id),
                Note.tenant_id == uuid.UUID(self.tenant_id),
                Note.user_id == self.user_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_note(self, note_id: str, content: str) -> Optional[Note]:
        note = await self.get_note_by_id(note_id)
        if not note:
            return None
        note.content = content
        await self.db.commit()
        await self.db.refresh(note)
        return note

    async def delete_note(self, note_id: str) -> bool:
        note = await self.get_note_by_id(note_id)
        if not note:
            return False
        await self.db.delete(note)
        await self.db.commit()
        return True