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

    mind_map: always resolves to sources_only at generation time regardless of context_mode
    (chat transcript and selection_text are ignored for mind_map).
    """

    task_type: Literal[
        "quiz",
        "flashcards",
        "mind_map",
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
    include_ncert_global: bool = Field(
        default=False,
        description="When true, retrieve from NCERT global Pinecone namespace using scope filters.",
    )
    ncert_class: Optional[int] = Field(None, ge=12, le=12)
    ncert_subject: Optional[str] = Field(None, description="Subject slug, e.g. science")
    ncert_chapter_no: Optional[int] = Field(None, ge=1)
    ncert_chapter_name: Optional[str] = Field(
        None, description="Lowercase chapter name filter for NCERT global retrieval"
    )

    def _has_ncert_scope(self) -> bool:
        return bool(
            self.include_ncert_global
            and self.ncert_class is not None
            and (self.ncert_subject or "").strip()
            and (
                self.ncert_chapter_no is not None
                or (self.ncert_chapter_name or "").strip()
            )
        )

    @model_validator(mode="after")
    def validate_by_context_mode(self) -> "StudioRequest":
        mode = self.context_mode
        sids = [str(s).strip() for s in (self.source_ids or []) if s is not None and str(s).strip()]
        has_ncert = self._has_ncert_scope()

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
            if len(sids) < 1 and not has_ncert:
                raise ValueError("chat_hybrid requires at least one source_id or NCERT scope")
            ct = (self.chat_transcript or "").strip()
            if not ct:
                raise ValueError("chat_hybrid requires non-empty chat_transcript")
            self.source_ids = sids
            self.chat_transcript = ct
            return self

        # sources_only
        if len(sids) < 1 and not has_ncert:
            raise ValueError("sources_only requires at least one source_id or NCERT scope")
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


class SlideDeckResponse(BaseModel):
    """Slide deck generation response."""

    task_type: Literal["slide_deck"] = "slide_deck"
    content: str = Field(..., description="Markdown outline for slide deck")
