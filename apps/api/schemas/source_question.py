"""Schemas for source question extraction."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class SourceQuestionSummary(BaseModel):
    id: str
    source_id: str
    question_number: int
    section_label: Optional[str] = None
    preview: str
    page_hint: Optional[int] = None
    sort_order: int = 0
    confidence: Optional[str] = None


class SourceQuestionDetail(SourceQuestionSummary):
    full_text: str
    source_title: Optional[str] = None


class SourceQuestionListResponse(BaseModel):
    status: str = Field(..., description="idle | processing | ready | failed")
    question_count: int = 0
    extraction_version: int = 0
    error: Optional[str] = None
    source_id: Optional[str] = None
    questions: List[SourceQuestionSummary] = Field(default_factory=list)


class SourceQuestionExtractResponse(SourceQuestionListResponse):
    pass
