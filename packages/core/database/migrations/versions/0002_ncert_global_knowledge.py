"""ncert global knowledge tables

Revision ID: 0002_ncert_global_knowledge
Revises: 0001_initial_schema
Create Date: 2026-04-02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_ncert_global_knowledge"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ncert_global_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("class", sa.SmallInteger(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("chapter_no", sa.Integer(), nullable=True),
        sa.Column("chapter_name", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=False),
        sa.Column("storage_key", sa.String(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="processing"),
        sa.Column("chunks_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("uploaded_by_clerk_user_id", sa.String(), nullable=False),
        sa.Column("pinecone_namespace", sa.String(), nullable=False, server_default="NcertDataGlobal"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_ncert_global_documents_class", "ncert_global_documents", ["class"], unique=False)
    op.create_index("ix_ncert_global_documents_subject", "ncert_global_documents", ["subject"], unique=False)
    op.create_index("ix_ncert_global_documents_status", "ncert_global_documents", ["status"], unique=False)
    op.create_index(
        "ix_ncert_global_documents_class_subject",
        "ncert_global_documents",
        ["class", "subject"],
        unique=False,
    )
    op.create_index(
        "ix_ncert_global_documents_created_at",
        "ncert_global_documents",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_ncert_global_documents_uploaded_by",
        "ncert_global_documents",
        ["uploaded_by_clerk_user_id"],
        unique=False,
    )

    op.create_table(
        "ncert_global_ingestion_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ncert_global_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(), nullable=False, server_default="running"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("context_llm_prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("context_llm_completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("context_llm_cost_usd", sa.Numeric(14, 6), nullable=False, server_default="0"),
        sa.Column("embedding_prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("embedding_cost_usd", sa.Numeric(14, 6), nullable=False, server_default="0"),
        sa.Column("total_cost_usd", sa.Numeric(14, 6), nullable=False, server_default="0"),
        sa.Column("chunks_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_ncert_global_ingestion_runs_document_id",
        "ncert_global_ingestion_runs",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_ncert_global_ingestion_runs_status",
        "ncert_global_ingestion_runs",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ncert_global_ingestion_runs_status", table_name="ncert_global_ingestion_runs")
    op.drop_index("ix_ncert_global_ingestion_runs_document_id", table_name="ncert_global_ingestion_runs")
    op.drop_table("ncert_global_ingestion_runs")
    op.drop_index("ix_ncert_global_documents_uploaded_by", table_name="ncert_global_documents")
    op.drop_index("ix_ncert_global_documents_created_at", table_name="ncert_global_documents")
    op.drop_index("ix_ncert_global_documents_class_subject", table_name="ncert_global_documents")
    op.drop_index("ix_ncert_global_documents_status", table_name="ncert_global_documents")
    op.drop_index("ix_ncert_global_documents_subject", table_name="ncert_global_documents")
    op.drop_index("ix_ncert_global_documents_class", table_name="ncert_global_documents")
    op.drop_table("ncert_global_documents")
