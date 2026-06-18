"""NCERT catalog chapters for Tutor Mode landing."""

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    Text,
    SmallInteger,
    Boolean,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from packages.core.database.connection import Base


class NcertCatalogChapter(Base):
    __tablename__ = "ncert_catalog_chapters"
    __table_args__ = (
        UniqueConstraint(
            "class_num",
            "subject_key",
            "chapter_no",
            name="uq_ncert_catalog_class_subject_chapter",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    class_num = Column(SmallInteger(), nullable=False, index=True)
    subject = Column(String, nullable=False)
    subsubject = Column(String, nullable=True)
    subject_key = Column(String, nullable=False, index=True)
    subject_slug = Column(String, nullable=False)
    chapter_no = Column(Integer, nullable=False)
    chapter_title = Column(String, nullable=False)
    topic_summary = Column(Text, nullable=True)
    filename = Column(String, nullable=False)
    pdf_path = Column(String, nullable=True)
    content_hash = Column(String, nullable=True, index=True)
    content_hash_prefix = Column(String, nullable=True)
    concepts = Column(JSON, nullable=False, default=list)
    concept_count = Column(Integer, nullable=False, default=0)
    featured_count = Column(Integer, nullable=False, default=0)
    is_featured_chapter = Column(Boolean, nullable=False, default=False)
    ingest_status = Column(String, nullable=False, default="pending", index=True)
    ncert_document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ncert_global_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    ncert_document = relationship("NcertGlobalDocument", foreign_keys=[ncert_document_id])
