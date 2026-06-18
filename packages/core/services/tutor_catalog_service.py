"""Tutor Mode catalog queries backed by ncert_catalog_chapters."""

from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.core.database.models.ncert_catalog import NcertCatalogChapter
from packages.core.database.models.notebook import Notebook
from packages.core.services.ncert_catalog_helpers import SUBJECT_ICONS, subject_display_label


def _concept_id(label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (label or "").strip().lower()).strip("-")
    return slug or "concept"


SUBJECT_ORDER = [
    "physics",
    "chemistry",
    "mathematics",
    "biology",
    "science",
    "history",
    "geography",
    "civics-polity",
    "economics",
]


class TutorCatalogService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_subjects(self, class_num: int) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(
                NcertCatalogChapter.subject_key,
                NcertCatalogChapter.subsubject,
                func.count(NcertCatalogChapter.id),
            )
            .where(NcertCatalogChapter.class_num == class_num)
            .group_by(NcertCatalogChapter.subject_key, NcertCatalogChapter.subsubject)
            .order_by(NcertCatalogChapter.subject_key)
        )
        subjects: List[Dict[str, Any]] = []
        for subject_key, subsubject, chapter_count in result.all():
            subjects.append(
                {
                    "id": subject_key,
                    "label": subject_display_label(subject_key, subsubject),
                    "icon": SUBJECT_ICONS.get(subject_key, "book"),
                    "chapter_count": int(chapter_count or 0),
                    "subject_slug": self._slug_for_key(subject_key),
                    "subsubject": subsubject,
                }
            )
        subjects.sort(
            key=lambda s: (
                SUBJECT_ORDER.index(s["id"]) if s["id"] in SUBJECT_ORDER else 99,
                s["label"],
            )
        )
        return subjects

    async def list_chapters(self, class_num: int, subject_key: str) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(NcertCatalogChapter)
            .options(selectinload(NcertCatalogChapter.ncert_document))
            .where(
                NcertCatalogChapter.class_num == class_num,
                NcertCatalogChapter.subject_key == subject_key,
            )
            .order_by(NcertCatalogChapter.chapter_no)
        )
        chapters = list(result.scalars().all())
        return [self._chapter_payload(ch) for ch in chapters]

    async def list_concepts(self, class_num: int, subject_key: str, chapter_no: int) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(NcertCatalogChapter).where(
                NcertCatalogChapter.class_num == class_num,
                NcertCatalogChapter.subject_key == subject_key,
                NcertCatalogChapter.chapter_no == chapter_no,
            )
        )
        chapter = result.scalar_one_or_none()
        if not chapter:
            return [{"id": "all", "label": "All concepts"}]

        concepts = [{"id": "all", "label": "All concepts"}]
        raw = chapter.concepts if isinstance(chapter.concepts, list) else []
        for label in raw:
            if isinstance(label, str) and label.strip():
                concepts.append({"id": _concept_id(label), "label": label.strip()})
        return concepts

    async def get_chapter(
        self, class_num: int, subject_key: str, chapter_no: int
    ) -> Optional[NcertCatalogChapter]:
        result = await self.db.execute(
            select(NcertCatalogChapter).where(
                NcertCatalogChapter.class_num == class_num,
                NcertCatalogChapter.subject_key == subject_key,
                NcertCatalogChapter.chapter_no == chapter_no,
            )
        )
        return result.scalar_one_or_none()

    async def list_featured_notebooks(
        self,
        *,
        tenant_id: str,
        user_id: str,
        class_num: int,
        subject_key: str,
        chapter_no: int,
    ) -> List[Dict[str, Any]]:
        tenant_uuid = uuid.UUID(tenant_id)
        result = await self.db.execute(
            select(Notebook).where(
                Notebook.tenant_id == tenant_uuid,
                Notebook.user_id == user_id,
                Notebook.is_featured.is_(True),
                Notebook.mode == "tutor",
            )
        )
        notebooks = list(result.scalars().all())
        out: List[Dict[str, Any]] = []
        for nb in notebooks:
            scope = (nb.settings or {}).get("tutor_scope") if isinstance(nb.settings, dict) else {}
            if not isinstance(scope, dict):
                continue
            if int(scope.get("class_num") or 0) != class_num:
                continue
            sk = scope.get("subject_key") or scope.get("subject_slug")
            if sk != subject_key:
                continue
            if int(scope.get("chapter_no") or 0) != chapter_no:
                continue
            out.append(
                {
                    "id": str(nb.id),
                    "title": nb.title,
                    "slug": nb.slug,
                    "focus": nb.focus,
                    "mastery_percent": nb.mastery_percent,
                }
            )
        return out

    def _slug_for_key(self, subject_key: str) -> str:
        if subject_key in ("mathematics", "science", "physics", "chemistry", "biology"):
            return subject_key
        return "social_science"

    def _chapter_payload(self, ch: NcertCatalogChapter) -> Dict[str, Any]:
        indexed = ch.ingest_status == "indexed" or ch.ncert_document_id is not None
        doc = ch.ncert_document
        filter_chapter_name = ""
        if doc and (doc.chapter_name or "").strip():
            filter_chapter_name = doc.chapter_name.strip().lower()
        elif (ch.chapter_title or "").strip():
            filter_chapter_name = ch.chapter_title.strip().lower()
        chunks_count = int(doc.chunks_count or 0) if doc else 0
        return {
            "chapter_no": ch.chapter_no,
            "title": ch.chapter_title,
            "chapter_title": ch.chapter_title,
            "filter_chapter_name": filter_chapter_name or None,
            "subject_slug": ch.subject_slug,
            "ncert_document_id": str(ch.ncert_document_id) if ch.ncert_document_id else None,
            "chunks_count": chunks_count,
            "summary": ch.topic_summary,
            "featured_count": ch.featured_count,
            "concept_count": ch.concept_count,
            "is_featured_chapter": bool(ch.is_featured_chapter),
            "indexed": indexed,
            "ingest_status": ch.ingest_status,
        }
