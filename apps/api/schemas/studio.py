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
    """Infographic generation response."""
    task_type: Literal["infographic"] = "infographic"
    content: str = Field(..., description="Visual brief description for infographic")
    image_url: Optional[str] = Field(None, description="URL of the generated infographic image")
    revised_prompt: Optional[str] = Field(None, description="DALL-E revised prompt used for image generation")
    image_error: Optional[str] = Field(None, description="Error message if image generation failed")


class SlideDeckResponse(BaseModel):
    """Slide deck generation response."""
    task_type: Literal["slide_deck"] = "slide_deck"
    content: str = Field(..., description="Markdown outline for slide deck")



