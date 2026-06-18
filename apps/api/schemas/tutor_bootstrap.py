"""Schemas for tutor notebook bootstrap and follow-up suggestions."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class TutorSuggestionItem(BaseModel):
    label: str
    prompt: str


class TutorStudioRecommendation(BaseModel):
    type: Literal["flashcards", "quiz", "mind_map", "slide_deck"]
    reason: str = ""
    auto_generate: bool = False


class TutorBootstrapResponse(BaseModel):
    opening_summary: str
    suggestions: List[TutorSuggestionItem]
    studio_recommendations: List[TutorStudioRecommendation]
    chat_id: Optional[str] = None
    cached: bool = False


class TutorFollowUpsRequest(BaseModel):
    notebook_id: str
    user_message: str
    assistant_message: str


class TutorFollowUpsResponse(BaseModel):
    follow_ups: List[str] = Field(default_factory=list)
