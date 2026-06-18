"""Home dashboard summary aggregation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.database.models.notebook import Notebook
from packages.core.database.models.studio_feature import StudioFeature
from packages.core.services.notebook_service import NotebookService


def _format_relative(iso: Optional[datetime]) -> str:
    if not iso:
        return 'Not studied yet'
    now = datetime.now(timezone.utc)
    if iso.tzinfo is None:
        iso = iso.replace(tzinfo=timezone.utc)
    diff = now - iso
    hours = int(diff.total_seconds() // 3600)
    days = int(diff.total_seconds() // 86400)
    if hours < 1:
        return 'Just now'
    if hours < 24:
        return f'{hours} {"hour" if hours == 1 else "hours"} ago'
    if days == 1:
        return 'Yesterday'
    if days < 7:
        return f'{days} days ago'
    return 'Last week'


class HomeSummaryService:
    def __init__(self, db: AsyncSession, tenant_id: str, user_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.notebooks = NotebookService(db, tenant_id, user_id)

    async def get_summary(self) -> Dict[str, Any]:
        notebooks = await self.notebooks.list_notebooks(limit=100)
        total = len(notebooks)

        quiz_count = 0
        strong = 0
        attention = 0
        mastery_values: List[int] = []

        for nb in notebooks:
            if isinstance(nb.mastery_percent, int):
                mastery_values.append(nb.mastery_percent)
                if nb.mastery_percent >= 75:
                    strong += 1
                elif nb.mastery_percent < 60:
                    attention += 1

        try:
            quiz_count = int(
                await self.db.scalar(
                    select(func.count(StudioFeature.id)).where(
                        StudioFeature.tenant_id == self.notebooks.tenant_id,
                        StudioFeature.user_id == self.user_id,
                        StudioFeature.type == 'quiz',
                    )
                )
                or 0
            )
        except Exception:
            quiz_count = 0

        syllabus_pct = round(sum(mastery_values) / len(mastery_values)) if mastery_values else 0

        sorted_notebooks = sorted(
            notebooks,
            key=lambda n: (
                n.last_studied_at or datetime.min.replace(tzinfo=timezone.utc),
                n.updated_at or datetime.min.replace(tzinfo=timezone.utc),
            ),
            reverse=True,
        )

        focus_nb = sorted_notebooks[0] if sorted_notebooks else None
        focus_concept = None
        if focus_nb:
            focus_concept = {
                'subject': focus_nb.subject or 'Your subject',
                'topic': focus_nb.focus or focus_nb.title,
                'decay_label': 'Review this week' if focus_nb.mastery_percent and focus_nb.mastery_percent < 70 else 'On track',
            }

        continue_learning = []
        for nb in sorted_notebooks[:4]:
            continue_learning.append(
                {
                    'id': str(nb.id),
                    'slug': nb.slug,
                    'title': nb.title,
                    'subject': nb.subject or '—',
                    'topic': nb.focus or nb.subtitle or 'Open notebook',
                    'progress': nb.mastery_percent if isinstance(nb.mastery_percent, int) else 0,
                    'lastStudied': _format_relative(nb.last_studied_at or nb.updated_at),
                }
            )

        performance_line = (
            f'{strong} strong concepts across {total} notebooks'
            if total
            else 'Create a notebook to start tracking progress'
        )

        return {
            'overview_metrics': {
                'syllabus_percent': syllabus_pct,
                'tests_completed': quiz_count,
                'strong_concepts': strong,
                'needs_attention': attention,
            },
            'focus_concept': focus_concept,
            'continue_learning': continue_learning,
            'performance_line': performance_line,
        }
