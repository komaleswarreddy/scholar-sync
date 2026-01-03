"""
Tenant Model

Represents a school/tenant in the multi-tenant system.
Each tenant has a unique subdomain and isolated data.
"""

from sqlalchemy import Column, String, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class Tenant(Base):
    """
    Tenant/School entity.
    
    Attributes:
        id: Unique tenant identifier (UUID)
        subdomain: Unique subdomain (e.g., "lincoln")
        name: Display name of the school
        settings: JSON configuration (colors, branding, etc.)
        created_at: Timestamp of creation
    """
    __tablename__ = "tenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subdomain = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    settings = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    sources = relationship("Source", back_populates="tenant", cascade="all, delete-orphan")
    chats = relationship("Chat", back_populates="tenant", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="tenant", cascade="all, delete-orphan")
