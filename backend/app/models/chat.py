"""
Chat Models
Represents chat sessions and messages for RAG-based conversations.
Each chat belongs to a tenant and user, with messages containing citations.
"""

from sqlalchemy import Column, String, ForeignKey, DateTime, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class Chat(Base):
    """
    Chat session entity.
    
    Attributes:
        id: Unique chat identifier
        tenant_id: Foreign key to tenants table
        user_id: Clerk user ID
        title: Optional chat title (auto-generated from first message)
        created_at: Timestamp of creation
    """
    __tablename__ = "chats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)  # Clerk user ID
    title = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")


class Message(Base):
    """
    Chat message entity.
    
    Attributes:
        id: Unique message identifier
        chat_id: Foreign key to chats table
        role: Message role ('user' or 'assistant')
        content: Message text content
        citations: JSON array of citation references [{"source_id": "...", "chunk_id": "...", "text": "..."}]
        feedback: User feedback ('thumbs_up', 'thumbs_down', or None)
        created_at: Timestamp of creation
    """
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id"), nullable=False, index=True)
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    citations = Column(JSON, default=[])  # Array of citation objects
    feedback = Column(String, nullable=True)  # 'thumbs_up', 'thumbs_down', or None
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    chat = relationship("Chat", back_populates="messages")
