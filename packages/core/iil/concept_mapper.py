"""Map interactions to curriculum Concept nodes."""

from __future__ import annotations

import logging
import re
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.database.models.concept import Concept
from packages.core.database.models.notebook import Notebook

logger = logging.getLogger(__name__)


def _slugify(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "concept"


async def map_concept_from_notebook(
    db: AsyncSession,
    notebook_id: Optional[str],
    *,
    explicit_concept: Optional[str] = None,
) -> Optional[UUID]:
    """Tutor mode: resolve concept from notebook curriculum_scope or explicit concept string."""
    if explicit_concept:
        slug = _slugify(explicit_concept)
        result = await db.execute(
            select(Concept).where(Concept.slug == slug).limit(1)
        )
        row = result.scalar_one_or_none()
        if row:
            return row.id

    if not notebook_id:
        return None
    try:
        nb_uuid = UUID(str(notebook_id))
    except ValueError:
        return None

    result = await db.execute(select(Notebook).where(Notebook.id == nb_uuid))
    notebook = result.scalar_one_or_none()
    if not notebook:
        return None

    scope = getattr(notebook, "curriculum_scope", None) or {}
    if isinstance(scope, dict):
        concept_name = scope.get("concept") or scope.get("topic")
        class_num = scope.get("class") or scope.get("class_num")
        subject_key = scope.get("subject_key") or scope.get("subject")
        chapter_no = scope.get("chapter_no") or scope.get("chapter")
        if concept_name:
            slug = _slugify(str(concept_name))
            q = select(Concept).where(Concept.slug == slug)
            if class_num is not None:
                q = q.where(Concept.class_num == int(class_num))
            if subject_key:
                q = q.where(Concept.subject_key == str(subject_key))
            if chapter_no is not None:
                q = q.where(Concept.chapter_no == int(chapter_no))
            result = await db.execute(q.limit(1))
            row = result.scalar_one_or_none()
            if row:
                return row.id
    return None


async def map_concept_from_query(db: AsyncSession, query: str) -> Optional[UUID]:
    """Exploratory mode: best-effort match query tokens against concept names."""
    q = (query or "").strip().lower()
    if len(q) < 4:
        return None
    result = await db.execute(select(Concept).limit(500))
    concepts = result.scalars().all()
    best: Optional[Concept] = None
    best_len = 0
    for c in concepts:
        name = (c.name or "").lower()
        if len(name) >= 4 and name in q and len(name) > best_len:
            best = c
            best_len = len(name)
    return best.id if best else None
