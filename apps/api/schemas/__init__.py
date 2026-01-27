"""
API Schemas

Pydantic models for API request/response validation.
"""

from apps.api.schemas.chat import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatStreamEvent,
    Citation,
    ChatCreateRequest,
    ChatUpdateRequest,
    ChatListItemResponse,
    ChatListResponse,
    MessageResponse,
    MessageCreateRequest,
)
from apps.api.schemas.source import (
    SourceResponse,
    SourceItem,
    SourceListResponse,
)
from apps.api.schemas.studio import (
    StudioRequest,
    QuizQuestion,
    QuizResponse,
    Flashcard,
    FlashcardsResponse,
    MindMapResponse,
    ReportResponse,
    InfographicResponse,
    SlideDeckResponse,
)

__all__ = [
    # Chat
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "ChatStreamEvent",
    "Citation",
    "ChatCreateRequest",
    "ChatUpdateRequest",
    "ChatListItemResponse",
    "ChatListResponse",
    "MessageResponse",
    "MessageCreateRequest",
    # Source
    "SourceResponse",
    "SourceItem",
    "SourceListResponse",
    # Studio
    "StudioRequest",
    "QuizQuestion",
    "QuizResponse",
    "Flashcard",
    "FlashcardsResponse",
    "MindMapResponse",
    "ReportResponse",
    "InfographicResponse",
    "SlideDeckResponse",
]
