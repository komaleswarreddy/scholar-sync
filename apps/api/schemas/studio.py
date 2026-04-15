"""
Studio Request/Response Schemas

Pydantic models for Studio generation API validation.
"""

from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Literal, Dict, Any

StudioContextMode = Literal["sources_only", "chat_hybrid", "selection_only"]

_STUDIO_CHAT_TRANSCRIPT_MAX = 120_000
_STUDIO_SELECTION_TEXT_MAX = 50_000
_SELECTION_TEXT_MIN_LEN = 15


class StudioRequest(BaseModel):
    """
    Request schema for Studio generation.

    context_mode:
      - sources_only: retrieval from source_ids only (default).
      - chat_hybrid: requires source_ids + chat_transcript; ~60/40 chat vs sources in prompt.
      - selection_only: requires selection_text; no retrieval; source_ids should be empty.
    """

    task_type: Literal[
        "quiz",
        "flashcards",
        "mind_map",
        "report",
        "infographic",
        "slide_deck",
    ] = Field(..., description="Type of generation task")
    source_ids: List[str] = Field(
        default_factory=list,
        description="Source IDs for retrieval (required for sources_only and chat_hybrid)",
    )
    context_mode: StudioContextMode = Field(
        default="sources_only",
        description="How to assemble context: sources_only | chat_hybrid | selection_only",
    )
    chat_transcript: Optional[str] = Field(
        None,
        max_length=_STUDIO_CHAT_TRANSCRIPT_MAX,
        description="Formatted conversation for chat_hybrid mode",
    )
    selection_text: Optional[str] = Field(
        None,
        max_length=_STUDIO_SELECTION_TEXT_MAX,
        description="Highlighted text only for selection_only mode",
    )
    custom_instructions: Optional[str] = Field(None, description="Custom generation instructions")
    retrieval_focus: Optional[str] = Field(
        None,
        description=(
            "Optional raw topic/focus string for vector retrieval (separate from format instructions). "
            "Ignored for task_type 'flashcards' — flashcards always use broad studio queries only."
        ),
    )
    report_format: Optional[
        Literal[
            "integrated",
            "briefing",
            "study_guide",
            "newsletter",
            "thematic_summary",
        ]
    ] = Field(
        None,
        description="Tailored report format (Studio Reports modal). Ignored when task_type is not 'report'.",
    )

    @model_validator(mode="after")
    def validate_by_context_mode(self) -> "StudioRequest":
        mode = self.context_mode
        sids = [str(s).strip() for s in (self.source_ids or []) if s is not None and str(s).strip()]

        if mode == "selection_only":
            st = (self.selection_text or "").strip()
            if len(st) < _SELECTION_TEXT_MIN_LEN:
                raise ValueError(
                    f"selection_only requires selection_text with at least {_SELECTION_TEXT_MIN_LEN} characters"
                )
            self.source_ids = []
            self.selection_text = st
            return self

        if mode == "chat_hybrid":
            if len(sids) < 1:
                raise ValueError("chat_hybrid requires at least one source_id")
            ct = (self.chat_transcript or "").strip()
            if not ct:
                raise ValueError("chat_hybrid requires non-empty chat_transcript")
            self.source_ids = sids
            self.chat_transcript = ct
            return self

        # sources_only
        if len(sids) < 1:
            raise ValueError("sources_only requires at least one source_id")
        self.source_ids = sids
        return self


class QuizQuestion(BaseModel):
    """Quiz question structure."""

    question: str
    options: List[str] = Field(..., min_length=2, max_length=4)
    correct_answer: str
    explanation: str


class QuizResponse(BaseModel):
    """Quiz generation response."""

    task_type: Literal["quiz"] = "quiz"
    data: Dict[str, Any] = Field(..., description="Quiz data with title and questions")


class Flashcard(BaseModel):
    """Flashcard structure."""

    front: str
    back: str


class FlashcardsResponse(BaseModel):
    """Flashcards generation response."""

    task_type: Literal["flashcards"] = "flashcards"
    data: List[Flashcard]


class MindMapResponse(BaseModel):
    """Mind map generation response."""

    task_type: Literal["mind_map"] = "mind_map"
    content: str = Field(..., description="Markdown/Mermaid syntax for mind map")


class ReportResponse(BaseModel):
    """Report generation response."""

    task_type: Literal["report"] = "report"
    content: str = Field(..., description="Comprehensive report text")


class InfographicResponse(BaseModel):
    """Infographic generation response — structured data rendered as HTML by the frontend."""

    task_type: Literal["infographic"] = "infographic"
    content: str = Field(..., description="Markdown bullet summary for the infographic")
    infographic_data: Optional[Dict[str, Any]] = Field(
        None, description="Structured JSON for frontend rendering (title, layout, sections, etc.)"
    )
    summary_bullets: Optional[List[str]] = Field(
        None, description="3-4 short learner-facing takeaway bullets"
    )


class SlideDeckResponse(BaseModel):
    """Slide deck generation response."""

    task_type: Literal["slide_deck"] = "slide_deck"
    content: str = Field(..., description="Markdown outline for slide deck")
