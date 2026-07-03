"""Curriculum concept taxonomy for IIL concept_node mapping."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, SmallInteger, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from packages.core.database.connection import Base


class Concept(Base):
    """A curriculum concept node (seeded from NCERT chapter concepts JSON)."""

    __tablename__ = "concepts"
    __table_args__ = (
        UniqueConstraint(
            "board",
            "class_num",
            "subject_key",
            "chapter_no",
            "slug",
            name="uq_concepts_board_class_subject_chapter_slug",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    board = Column(String, nullable=False, default="CBSE", index=True)
    class_num = Column(SmallInteger(), nullable=False, index=True)
    subject_key = Column(String, nullable=False, index=True)
    chapter_no = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, index=True)
    ncert_chapter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ncert_catalog_chapters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    parent_concept_id = Column(
        UUID(as_uuid=True),
        ForeignKey("concepts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    parent = relationship("Concept", remote_side="Concept.id", backref="children")
