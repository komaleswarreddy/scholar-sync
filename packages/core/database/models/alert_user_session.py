"""
Alert User Session Model

Stores user and session information when alerts are triggered related to
token consumption, cost, or security issues.
"""

from sqlalchemy import Column, String, ForeignKey, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from packages.core.database.connection import Base


class AlertUserSession(Base):
    """
    Alert User Session entity.
    
    Stores user_id and session_id when alerts are triggered for:
    - Token consumption issues
    - Cost spikes
    - Security-related alerts
    
    Attributes:
        id: Unique identifier
        tenant_id: Foreign key to tenants table
        user_id: Clerk user ID
        session_id: Chat/session ID where alert was triggered
        alert_type: Type of alert (token_spike, cost_spike, security, etc.)
        alert_message: Alert message/description
        severity: Alert severity (high, medium, low)
        created_at: Timestamp of creation
    """
    __tablename__ = "alert_user_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)  # Clerk user ID
    session_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # Chat/session ID
    alert_type = Column(String, nullable=False, index=True)  # token_spike, cost_spike, security, etc.
    alert_message = Column(Text, nullable=True)
    severity = Column(String, nullable=False, default='medium')  # high, medium, low
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    tenant = relationship("Tenant")
