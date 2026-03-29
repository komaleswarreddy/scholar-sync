"""
Studio Request/Response Schemas

Pydantic models for Studio generation API validation.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any


class StudioRequest(BaseModel):
    """
    Request schema for Studio generation.
    
    Attributes:
        task_type: Type of generation task
        source_ids: List of source IDs to use for generation
        custom_instructions: Optional custom instructions for generation
    """
    task_type: Literal[
        "quiz",
        "flashcards",
        "mind_map",
        "report",
        "infographic",
        "slide_deck"
    ] = Field(..., description="Type of generation task")
    source_ids: List[str] = Field(..., min_items=1, description="Source IDs for context")
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


class QuizQuestion(BaseModel):
    """Quiz question structure."""
    question: str
    options: List[str] = Field(..., min_items=2, max_items=4)
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
    infographic_data: Optional[Dict[str, Any]] = Field(None, description="Structured JSON for frontend rendering (title, layout, sections, etc.)")
    summary_bullets: Optional[List[str]] = Field(None, description="3-4 short learner-facing takeaway bullets")


class SlideDeckResponse(BaseModel):
    """Slide deck generation response."""
    task_type: Literal["slide_deck"] = "slide_deck"
    content: str = Field(..., description="Markdown outline for slide deck")



