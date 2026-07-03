"""IIL curation — candidates and derived artifacts

Revision ID: 0010_iil_curation
Revises: 0009_iil_foundation
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010_iil_curation"
down_revision = "0009_iil_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "curation_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("interaction_log_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("interaction_logs.id", ondelete="CASCADE"), nullable=True),
        sa.Column("feedback_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("interaction_feedback.id", ondelete="CASCADE"), nullable=True),
        sa.Column("concept_node_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False, server_default="interaction_chain"),
        sa.Column("candidate_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scoring_signals", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("reviewed_by", sa.String(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_curation_candidates_status", "curation_candidates", ["status"])
    op.create_index("ix_curation_candidates_tenant", "curation_candidates", ["tenant_id", "created_at"])

    op.create_table(
        "derived_knowledge_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("curation_candidates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("concept_node_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dimension_tags", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_interaction_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False, server_default="{}"),
        sa.Column("source_user_tier", sa.String(), nullable=True),
        sa.Column("confidence_score", sa.SmallInteger(), nullable=True),
        sa.Column("embedding_id", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_dka_concept", "derived_knowledge_artifacts", ["concept_node_id"])
    op.create_index("ix_dka_tenant_active", "derived_knowledge_artifacts", ["tenant_id", "is_active"])
    op.create_index("ix_dka_embedding_id", "derived_knowledge_artifacts", ["embedding_id"])


def downgrade() -> None:
    op.drop_table("derived_knowledge_artifacts")
    op.drop_table("curation_candidates")
