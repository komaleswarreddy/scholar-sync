"""
Chat Request/Response Schemas

Pydantic models for chat API validation.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime


class ChatMessage(BaseModel):
    """Individual chat message in history."""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """
    Request schema for chat endpoint.
    
    Attributes:
        message: User's question/query
        history: Previous messages in conversation (for context)
        active_source_ids: List of source IDs to include in RAG context
    """
    message: str = Field(..., min_length=1, description="User's question")
    history: List[ChatMessage] = Field(default=[], description="Conversation history")
    active_source_ids: List[str] = Field(..., min_items=1, description="Source IDs for context")


class Citation(BaseModel):
    """Citation reference from source."""
    source_id: str
    chunk_id: str
    text: str
    page_number: Optional[int] = None
    score: float


class ChatResponse(BaseModel):
    """Response schema for chat (non-streaming)."""
    content: str
    citations: List[Citation] = Field(default=[])
    message_id: str


class ChatStreamEvent(BaseModel):
    """Server-Sent Event for streaming chat."""
    event: str = Field(..., description="Event type: 'chunk', 'citation', 'done'")
    data: Dict = Field(..., description="Event data")


# Task C: Chat History Schemas
class ChatCreateRequest(BaseModel):
    """Request to create a new chat."""
    title: Optional[str] = Field(None, description="Chat title (auto-generated if not provided)")


class ChatUpdateRequest(BaseModel):
    """Request to update a chat."""
    title: Optional[str] = Field(None, description="Chat title")


class MessageResponse(BaseModel):
    """Response schema for a message."""
    id: str
    role: str
    content: str
    citations: List[Citation] = Field(default=[])
    feedback: Optional[str] = Field(None, description="User feedback: 'thumbs_up', 'thumbs_down', or None")
    created_at: datetime

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    """Response schema for a chat."""
    id: str
    title: Optional[str]
    created_at: datetime
    messages: List[MessageResponse] = Field(default=[])

    class Config:
        from_attributes = True


class ChatListItemResponse(BaseModel):
    """Response schema for chat list item (without messages)."""
    id: str
    title: Optional[str]
    created_at: datetime
    message_count: int = Field(default=0, description="Number of messages in chat")

    class Config:
        from_attributes = True


class ChatListResponse(BaseModel):
    """Response schema for list of chats."""
    chats: List[ChatListItemResponse]


class MessageCreateRequest(BaseModel):
    """Request to add a message to a chat."""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    citations: List[Citation] = Field(default=[], description="Citation references")