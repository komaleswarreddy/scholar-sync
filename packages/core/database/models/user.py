"""
User Model

User entity for role management.
"""

from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from packages.core.database.connection import Base


class User(Base):
    """
    User entity for role management.
    
    Attributes:
        id: Unique user identifier (UUID)
        email: User email address (unique)
        clerk_user_id: Clerk user ID (can be null until user logs in)
        role: User role ('admin', 'user', etc.)
        created_at: Timestamp of creation
        updated_at: Timestamp of last update
    """
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    clerk_user_id = Column(String, nullable=True, index=True)
    role = Column(String, default="user", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
