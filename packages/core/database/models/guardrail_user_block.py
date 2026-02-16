"""
Guardrail User Block Model

Stores user details when guardrail blocks exceed 3 for any user.
"""

from sqlalchemy import Column, String, ForeignKey, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from packages.core.database.connection import Base


class GuardrailUserBlock(Base):
    """
    Guardrail User Block entity.
    
    Stores user details when guardrail blocks exceed 3 for any user.
    
    Attributes:
        id: Unique identifier
        tenant_id: Foreign key to tenants table
        user_id: Clerk user ID
        user_name: User's name (first_name + last_name or email)
        session_id: Chat/session ID where block occurred
        block_count: Number of blocks for this user
        block_reason: Reason for the block (safety_filter, injection_detection, etc.)
        created_at: Timestamp of creation
        updated_at: Timestamp of last update
    """
    __tablename__ = "guardrail_user_blocks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)  # Clerk user ID
    user_name = Column(String, nullable=True)  # User's name for display
    session_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # Chat/session ID
    block_count = Column(Integer, nullable=False, default=0)
    block_reason = Column(String, nullable=True)  # safety_filter, injection_detection, intent_gate, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant")
