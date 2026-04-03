"""
NCERT global knowledge (admin-uploaded corpus; Pinecone namespace NcertDataGlobal).
"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Numeric, Text, SmallInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from packages.core.database.connection import Base


class NcertGlobalDocument(Base):
    __tablename__ = "ncert_global_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # DB column "class" (NCERT grade); Python attr class_num
    class_num = Column("class", SmallInteger(), nullable=False, index=True)
    subject = Column(String, nullable=False, index=True)
    chapter_no = Column(Integer, nullable=True)
    chapter_name = Column(String, nullable=True)
    title = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    storage_key = Column(String, nullable=False)
    content_hash = Column(String, nullable=True)
    status = Column(String, nullable=False, default="processing", index=True)
    chunks_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    uploaded_by_clerk_user_id = Column(String, nullable=False, index=True)
    pinecone_namespace = Column(String, nullable=False, default="NcertDataGlobal")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    ingestion_runs = relationship(
        "NcertGlobalIngestionRun",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class NcertGlobalIngestionRun(Base):
    __tablename__ = "ncert_global_ingestion_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ncert_global_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(String, nullable=False, default="running", index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    context_llm_prompt_tokens = Column(Integer, nullable=False, default=0)
    context_llm_completion_tokens = Column(Integer, nullable=False, default=0)
    context_llm_cost_usd = Column(Numeric(14, 6), nullable=False, default=0)
    embedding_prompt_tokens = Column(Integer, nullable=False, default=0)
    embedding_cost_usd = Column(Numeric(14, 6), nullable=False, default=0)
    total_cost_usd = Column(Numeric(14, 6), nullable=False, default=0)
    chunks_processed = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)

    document = relationship("NcertGlobalDocument", back_populates="ingestion_runs")
