"""Notebook API schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class NotebookCreateRequest(BaseModel):
    title: Optional[str] = Field(default="Untitled notebook")
    mode: str = Field(default="exploratory", description="exploratory | tutor | problem_solver")
    class_level: Optional[str] = None
    subject: Optional[str] = None
    focus: Optional[str] = None
    settings: Optional[dict] = None


class NotebookUpdateRequest(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    focus: Optional[str] = None
    settings: Optional[dict] = None
    touch_last_studied: bool = False


class NotebookResponse(BaseModel):
    id: str
    title: str
    slug: str
    mode: str
    subtitle: Optional[str] = None
    subject: Optional[str] = None
    class_level: Optional[str] = None
    focus: Optional[str] = None
    mastery_percent: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_studied_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotebookDetailResponse(NotebookResponse):
    sources_count: int = 0
    chats_count: int = 0
    notes_count: int = 0
    study_assets_count: int = 0
    quizzes_count: int = 0
    settings: Optional[dict] = None


class NotebookListItemResponse(NotebookResponse):
    sources_count: int = 0
    notes_count: int = 0
    study_assets_count: int = 0
    quizzes_count: int = 0


class NotebookListResponse(BaseModel):
    notebooks: List[NotebookListItemResponse]
    total: int
    active_this_week: int = 0
