"""Home summary API schemas."""

from typing import Any, List, Optional

from pydantic import BaseModel


class OverviewMetrics(BaseModel):
    syllabus_percent: int = 0
    tests_completed: int = 0
    strong_concepts: int = 0
    needs_attention: int = 0


class FocusConcept(BaseModel):
    subject: str
    topic: str
    decay_label: str


class ContinueLearningItem(BaseModel):
    id: str
    slug: str
    title: str
    subject: str
    topic: str
    progress: int = 0
    lastStudied: str


class HomeSummaryResponse(BaseModel):
    overview_metrics: OverviewMetrics
    focus_concept: Optional[FocusConcept] = None
    continue_learning: List[ContinueLearningItem] = []
    performance_line: str = ''
