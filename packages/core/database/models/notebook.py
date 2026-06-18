"""
Notebook Model

Represents an exploratory or tutor workspace scoped to a tenant and user.
"""

from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from packages.core.database.connection import Base


class Notebook(Base):
    """Notebook workspace entity."""

    __tablename__ = "notebooks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False, default="Untitled notebook")
    slug = Column(String, nullable=False, index=True)
    mode = Column(String, nullable=False, default="exploratory")
    subtitle = Column(String, nullable=True)
    subject = Column(String, nullable=True)
    class_level = Column(String, nullable=True)
    focus = Column(String, nullable=True)
    mastery_percent = Column(Integer, nullable=True)
    settings = Column(JSON, default=dict)
    is_featured = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_studied_at = Column(DateTime(timezone=True), nullable=True)

    tenant = relationship("Tenant", back_populates="notebooks")
    sources = relationship("Source", back_populates="notebook", cascade="all, delete-orphan")
    chats = relationship("Chat", back_populates="notebook", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="notebook", cascade="all, delete-orphan")
