"""
Note Model

Represents saved notes (manual entries or saved chat responses).
Each note belongs to a tenant and user.
"""

from sqlalchemy import Column, String, ForeignKey, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class Note(Base):
    """
    Note entity.
    
    Attributes:
        id: Unique note identifier
        tenant_id: Foreign key to tenants table
        user_id: Clerk user ID
        content: Note text content
        source_ref_id: Optional reference to a chat message (if saved from chat)
        created_at: Timestamp of creation
        updated_at: Timestamp of last update
    """
    __tablename__ = "notes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)  # Clerk user ID
    content = Column(Text, nullable=False)
    source_ref_id = Column(UUID(as_uuid=True), nullable=True)  # Optional link to message
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="notes")


