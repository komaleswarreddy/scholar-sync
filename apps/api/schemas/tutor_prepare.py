"""Schemas for unified tutor notebook prepare."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from apps.api.schemas.tutor_bootstrap import (
    TutorBootstrapResponse,
    TutorStudioRecommendation,
    TutorSuggestionItem,
)


class TutorPrepareScope(BaseModel):
    class_num: int = Field(..., ge=12, le=12)
    subject_key: str
    subject_slug: Optional[str] = None
    subsubject: Optional[str] = None
    chapter_no: int = Field(..., ge=1)
    chapter_title: str
    filter_chapter_name: Optional[str] = None
    ncert_document_id: Optional[str] = None
    chunks_count: Optional[int] = None
    concept: Optional[str] = None


class TutorPrepareRequest(BaseModel):
    title: str
    class_level: Optional[str] = None
    subject: Optional[str] = None
    focus: Optional[str] = None
    tutor_scope: TutorPrepareScope


class TutorPrepareAsset(BaseModel):
    id: str
    type: Literal["flashcards", "quiz", "mind_map", "slide_deck"]
    title: str


class TutorPrepareTiming(BaseModel):
    create_notebook_ms: int = 0
    ncert_retrieval_ms: int = 0
    ncert_cache_hit: int = 0
    bootstrap_llm_ms: int = 0
    studio_parallel_ms: int = 0
    persist_ms: int = 0
    total_ms: int = 0


class TutorPrepareResponse(BaseModel):
    notebook_id: str
    slug: str
    opening_summary: str
    suggestions: List[TutorSuggestionItem]
    studio_recommendations: List[TutorStudioRecommendation]
    chat_id: Optional[str] = None
    assets_created: int = 0
    assets: List[TutorPrepareAsset] = Field(default_factory=list)
    auto_types: List[str] = Field(default_factory=list)
    timing: TutorPrepareTiming
    partial_failure: bool = False


class TutorNcertWarmRequest(BaseModel):
    tutor_scope: TutorPrepareScope


class TutorNcertWarmResponse(BaseModel):
    ok: bool = True
    cached: bool = False
    context_chars: int = 0
    duration_ms: int = 0
