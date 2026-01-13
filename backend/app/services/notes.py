from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID, uuid4

from app.models.note import Note

class NotesService:
    """Service for managing notes."""

    def __init__(self, db: AsyncSession, tenant_id: UUID, user_id: str):
        self.db = db
        # ✅ Ensure tenant_id is always UUID
        if isinstance(tenant_id, str):
            self.tenant_id = UUID(tenant_id)
        else:
            self.tenant_id = tenant_id
        self.user_id = user_id

    async def create_note(self, content: str, source_ref_id: Optional[str] = None) -> Note:
        note = Note(
            id=uuid4(),
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            content=content,
            source_ref_id=UUID(source_ref_id) if source_ref_id else None,
        )
        self.db.add(note)
        await self.db.commit()
        await self.db.refresh(note)
        return note

    async def list_notes(self) -> List[Note]:
        result = await self.db.execute(
            select(Note).where(
                Note.tenant_id == self.tenant_id,
                Note.user_id == self.user_id
            )
        )
        return result.scalars().all()

    async def get_note_by_id(self, note_id: str) -> Optional[Note]:
        result = await self.db.execute(
            select(Note).where(
                Note.id == UUID(note_id),
                Note.tenant_id == self.tenant_id,
                Note.user_id == self.user_id
            )
        )
        return result.scalar_one_or_none()

    async def update_note(self, note_id: str, content: str) -> Optional[Note]:
        note = await self.get_note_by_id(note_id)
        if not note:
            return None
        note.content = content
        self.db.add(note)
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
