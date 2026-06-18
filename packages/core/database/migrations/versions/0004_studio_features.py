"""studio_features table

Revision ID: 0004_studio_features
Revises: 0003_notebooks
Create Date: 2026-06-05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_studio_features"
down_revision = "0003_notebooks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "studio_features",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("notebook_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("content", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("source_ids", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_studio_features_tenant_id", "studio_features", ["tenant_id"], unique=False)
    op.create_index("ix_studio_features_user_id", "studio_features", ["user_id"], unique=False)
    op.create_index("ix_studio_features_notebook_id", "studio_features", ["notebook_id"], unique=False)
    op.create_index("ix_studio_features_type", "studio_features", ["type"], unique=False)

    op.execute("ALTER TABLE public.studio_features ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.studio_features FORCE ROW LEVEL SECURITY;")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE public.studio_features FROM anon, authenticated;")


def downgrade() -> None:
    op.drop_index("ix_studio_features_type", table_name="studio_features")
    op.drop_index("ix_studio_features_notebook_id", table_name="studio_features")
    op.drop_index("ix_studio_features_user_id", table_name="studio_features")
    op.drop_index("ix_studio_features_tenant_id", table_name="studio_features")
    op.drop_table("studio_features")
