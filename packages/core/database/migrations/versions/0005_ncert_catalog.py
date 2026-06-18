"""ncert catalog chapters + notebooks.is_featured

Revision ID: 0005_ncert_catalog
Revises: 0004_studio_features
Create Date: 2026-06-05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_ncert_catalog"
down_revision = "0004_message_feedback_reason"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ncert_catalog_chapters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("class_num", sa.SmallInteger(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("subsubject", sa.String(), nullable=True),
        sa.Column("subject_key", sa.String(), nullable=False),
        sa.Column("subject_slug", sa.String(), nullable=False),
        sa.Column("chapter_no", sa.Integer(), nullable=False),
        sa.Column("chapter_title", sa.String(), nullable=False),
        sa.Column("topic_summary", sa.Text(), nullable=True),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("pdf_path", sa.String(), nullable=True),
        sa.Column("content_hash", sa.String(), nullable=True),
        sa.Column("content_hash_prefix", sa.String(), nullable=True),
        sa.Column("concepts", postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("concept_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("featured_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_featured_chapter", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("ingest_status", sa.String(), nullable=False, server_default="pending"),
        sa.Column(
            "ncert_document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ncert_global_documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "class_num",
            "subject_key",
            "chapter_no",
            name="uq_ncert_catalog_class_subject_chapter",
        ),
    )
    op.create_index("ix_ncert_catalog_class_num", "ncert_catalog_chapters", ["class_num"])
    op.create_index("ix_ncert_catalog_subject_key", "ncert_catalog_chapters", ["subject_key"])
    op.create_index("ix_ncert_catalog_content_hash", "ncert_catalog_chapters", ["content_hash"])
    op.create_index("ix_ncert_catalog_ingest_status", "ncert_catalog_chapters", ["ingest_status"])
    op.create_index(
        "ix_ncert_catalog_ncert_document_id",
        "ncert_catalog_chapters",
        ["ncert_document_id"],
    )

    op.add_column(
        "notebooks",
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("notebooks", "is_featured")
    op.drop_index("ix_ncert_catalog_ncert_document_id", table_name="ncert_catalog_chapters")
    op.drop_index("ix_ncert_catalog_ingest_status", table_name="ncert_catalog_chapters")
    op.drop_index("ix_ncert_catalog_content_hash", table_name="ncert_catalog_chapters")
    op.drop_index("ix_ncert_catalog_subject_key", table_name="ncert_catalog_chapters")
    op.drop_index("ix_ncert_catalog_class_num", table_name="ncert_catalog_chapters")
    op.drop_table("ncert_catalog_chapters")
