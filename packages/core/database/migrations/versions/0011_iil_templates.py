"""IIL exploration templates

Revision ID: 0011_iil_templates
Revises: 0010_iil_curation
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0011_iil_templates"
down_revision = "0010_iil_curation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exploration_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("concept_node_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_chain_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False, server_default="{}"),
        sa.Column("source_user_tier", sa.String(), nullable=False),
        sa.Column("dimension_sequence", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("template_prompts", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_exploration_templates_concept", "exploration_templates", ["concept_node_id"])
    op.create_index("ix_exploration_templates_tenant", "exploration_templates", ["tenant_id", "is_active"])


def downgrade() -> None:
    op.drop_table("exploration_templates")
