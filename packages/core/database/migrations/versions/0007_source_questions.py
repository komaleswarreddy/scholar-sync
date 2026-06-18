"""source_questions for multi-question paper extraction

Revision ID: 0007_source_questions
Revises: 0006_problem_solver
Create Date: 2026-06-15
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007_source_questions"
down_revision = "0006_problem_solver"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sources",
        sa.Column(
            "source_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )

    op.create_table(
        "source_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("notebook_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("notebooks.id"), nullable=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_number", sa.Integer(), nullable=False),
        sa.Column("section_label", sa.Text(), nullable=True),
        sa.Column("preview", sa.Text(), nullable=False),
        sa.Column("full_text", sa.Text(), nullable=False),
        sa.Column("page_hint", sa.Integer(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confidence", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_source_questions_source_id", "source_questions", ["source_id"])
    op.create_index("ix_source_questions_notebook_id", "source_questions", ["notebook_id"])
    op.create_index("ix_source_questions_tenant_id", "source_questions", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_source_questions_tenant_id", table_name="source_questions")
    op.drop_index("ix_source_questions_notebook_id", table_name="source_questions")
    op.drop_index("ix_source_questions_source_id", table_name="source_questions")
    op.drop_table("source_questions")
    op.drop_column("sources", "source_metadata")
