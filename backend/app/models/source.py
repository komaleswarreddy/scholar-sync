"""
Source Model

Represents uploaded study materials (PDFs, text, URLs) for a tenant.
Each source is tenant-scoped and can be selected for chat context.
"""

from sqlalchemy import Column, String, ForeignKey, DateTime, Enum as SQLEnum, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.core.database import Base


class SourceType(str, enum.Enum):
    """Types of sources that can be uploaded."""
    PDF = "pdf"
    TEXT = "text"
    URL = "url"


class SourceStatus(str, enum.Enum):
    """Status of source processing."""
    PROCESSING = "processing"
    INDEXED = "indexed"
    ERROR = "error"


class Source(Base):
    """
    Source document entity.
    
    Attributes:
        id: Unique source identifier
        tenant_id: Foreign key to tenants table (multi-tenancy)
        title: Display name of the source
        s3_key: S3 object key for the file
        type: Type of source (PDF, TEXT, URL)
        status: Processing status (processing, indexed, error)
        chunks_count: Number of chunks created
        error_message: Error message when processing fails (status is 'error')
        created_at: Timestamp of upload
    """
    __tablename__ = "sources"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    s3_key = Column(String, nullable=False)
    type = Column(String, default=SourceType.PDF.value, nullable=False)  # Store as string, use enum in code
    status = Column(String, default=SourceStatus.PROCESSING.value, nullable=False)  # Store as string, use enum in code
    chunks_count = Column(Integer, default=0, nullable=False)
    error_message = Column(String, nullable=True)  # Error message when status is 'error'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="sources")

