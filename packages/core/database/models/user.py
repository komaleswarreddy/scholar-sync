"""
User Model

Platform user with username/password auth and profile fields.
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from packages.core.database.connection import Base

VALID_ROLES = frozenset({"student", "teacher", "expert", "schooladmin"})


class User(Base):
    """
    Platform user scoped to a tenant.

    Attributes:
        id: Unique user identifier (UUID)
        tenant_id: Tenant this user belongs to
        username: Login username (unique per tenant)
        password_hash: bcrypt hash
        email: Optional contact email
        role: student | teacher | expert | schooladmin
        first_name, last_name, mobile, institute, class_level: profile fields
        is_active: soft-disable flag
        clerk_user_id: deprecated — kept for legacy rows
    """

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "username", name="uq_users_tenant_username"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    username = Column(String, nullable=True, index=True)
    password_hash = Column(String, nullable=True)
    email = Column(String, nullable=True, index=True)
    clerk_user_id = Column(String, nullable=True, index=True)
    role = Column(String, default="student", nullable=False)
    expertise_tier = Column(String, default="student", nullable=False, server_default="student")
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    mobile = Column(String, nullable=True)
    institute = Column(String, nullable=True)
    class_level = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
