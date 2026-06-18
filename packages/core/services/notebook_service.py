"""
Notebook Service

CRUD operations for notebook workspaces scoped by tenant and user.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.database.models.notebook import Notebook
from packages.core.database.models.source import Source
from packages.core.database.models.chat import Chat
from packages.core.database.models.note import Note

DEFAULT_NOTEBOOK_TITLE = "Untitled notebook"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "notebook"


class NotebookService:
    def __init__(self, db: AsyncSession, tenant_id: str, user_id: str):
        self.db = db
        self.tenant_id = uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
        self.user_id = user_id

    async def _unique_slug(self, base: str) -> str:
        candidate = base
        suffix = 1
        while True:
            result = await self.db.execute(
                select(Notebook.id).where(
                    Notebook.tenant_id == self.tenant_id,
                    Notebook.user_id == self.user_id,
                    Notebook.slug == candidate,
                )
            )
            if result.scalar_one_or_none() is None:
                return candidate
            suffix += 1
            candidate = f"{base}-{suffix}"

    async def create_notebook(
        self,
        *,
        title: str = DEFAULT_NOTEBOOK_TITLE,
        mode: str = "exploratory",
        class_level: Optional[str] = None,
        subject: Optional[str] = None,
        focus: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> Notebook:
        notebook_id = uuid.uuid4()
        base_slug = _slugify(title)
        if base_slug == "untitled-notebook":
            base_slug = f"untitled-notebook-{notebook_id.hex[:8]}"
        slug = await self._unique_slug(base_slug)

        notebook = Notebook(
            id=notebook_id,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            title=title,
            slug=slug,
            mode=mode,
            class_level=class_level,
            subject=subject,
            focus=focus,
            settings=settings or {},
        )
        self.db.add(notebook)
        await self.db.commit()
        await self.db.refresh(notebook)
        return notebook

    async def get_notebook(self, notebook_id: str) -> Optional[Notebook]:
        notebook_uuid = uuid.UUID(notebook_id)
        result = await self.db.execute(
            select(Notebook).where(
                Notebook.id == notebook_uuid,
                Notebook.tenant_id == self.tenant_id,
                Notebook.user_id == self.user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_notebook_by_slug(self, slug: str) -> Optional[Notebook]:
        result = await self.db.execute(
            select(Notebook).where(
                Notebook.slug == slug,
                Notebook.tenant_id == self.tenant_id,
                Notebook.user_id == self.user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_notebooks(self, limit: int = 50, offset: int = 0) -> List[Notebook]:
        result = await self.db.execute(
            select(Notebook)
            .where(
                Notebook.tenant_id == self.tenant_id,
                Notebook.user_id == self.user_id,
            )
            .order_by(Notebook.updated_at.desc().nullslast(), Notebook.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_active_this_week(self) -> int:
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        result = await self.db.scalar(
            select(func.count(Notebook.id)).where(
                Notebook.tenant_id == self.tenant_id,
                Notebook.user_id == self.user_id,
                Notebook.last_studied_at.isnot(None),
                Notebook.last_studied_at >= week_ago,
            )
        )
        return int(result or 0)

    async def get_notebook_list_counts(self, notebook_id: str) -> Dict[str, int]:
        base = await self.get_notebook_counts(notebook_id)
        if not base:
            return {
                "sources_count": 0,
                "notes_count": 0,
                "study_assets_count": 0,
                "quizzes_count": 0,
            }
        study_assets_count = 0
        quizzes_count = 0
        try:
            from packages.core.database.models.studio_feature import StudioFeature

            notebook_uuid = uuid.UUID(notebook_id)
            study_assets_count = int(
                await self.db.scalar(
                    select(func.count(StudioFeature.id)).where(
                        StudioFeature.notebook_id == notebook_uuid,
                        StudioFeature.tenant_id == self.tenant_id,
                        StudioFeature.user_id == self.user_id,
                    )
                )
                or 0
            )
            quizzes_count = int(
                await self.db.scalar(
                    select(func.count(StudioFeature.id)).where(
                        StudioFeature.notebook_id == notebook_uuid,
                        StudioFeature.tenant_id == self.tenant_id,
                        StudioFeature.user_id == self.user_id,
                        StudioFeature.type == "quiz",
                    )
                )
                or 0
            )
        except Exception:
            pass
        return {
            "sources_count": base.get("sources_count", 0),
            "notes_count": base.get("notes_count", 0),
            "study_assets_count": study_assets_count,
            "quizzes_count": quizzes_count,
        }

    async def update_notebook(
        self,
        notebook_id: str,
        *,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        focus: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
        touch_last_studied: bool = False,
    ) -> Optional[Notebook]:
        notebook = await self.get_notebook(notebook_id)
        if not notebook:
            return None
        if title is not None:
            notebook.title = title.strip() or DEFAULT_NOTEBOOK_TITLE
        if subtitle is not None:
            notebook.subtitle = subtitle
        if focus is not None:
            notebook.focus = focus
        if settings is not None:
            merged = dict(notebook.settings or {})
            merged.update(settings)
            notebook.settings = merged
        now = datetime.now(timezone.utc)
        notebook.updated_at = now
        if touch_last_studied:
            notebook.last_studied_at = now
        await self.db.commit()
        await self.db.refresh(notebook)
        return notebook

    async def delete_notebook(self, notebook_id: str) -> bool:
        notebook = await self.get_notebook(notebook_id)
        if not notebook:
            return False
        await self.db.delete(notebook)
        await self.db.commit()
        return True

    async def get_notebook_counts(self, notebook_id: str) -> dict:
        notebook_uuid = uuid.UUID(notebook_id)
        base = and_(
            Notebook.tenant_id == self.tenant_id,
            Notebook.user_id == self.user_id,
        )

        sources_count = await self.db.scalar(
            select(func.count(Source.id)).where(
                Source.notebook_id == notebook_uuid,
                Source.tenant_id == self.tenant_id,
                Source.user_id == self.user_id,
            )
        )
        chats_count = await self.db.scalar(
            select(func.count(Chat.id)).where(
                Chat.notebook_id == notebook_uuid,
                Chat.tenant_id == self.tenant_id,
                Chat.user_id == self.user_id,
            )
        )
        notes_count = await self.db.scalar(
            select(func.count(Note.id)).where(
                Note.notebook_id == notebook_uuid,
                Note.tenant_id == self.tenant_id,
                Note.user_id == self.user_id,
            )
        )

        notebook_exists = await self.db.scalar(
            select(func.count(Notebook.id)).where(Notebook.id == notebook_uuid).where(base)
        )
        if not notebook_exists:
            return {}

        return {
            "sources_count": int(sources_count or 0),
            "chats_count": int(chats_count or 0),
            "notes_count": int(notes_count or 0),
        }
