"""problem_solver sessions + steps

Revision ID: 0006_problem_solver
Revises: 0005_ncert_catalog
Create Date: 2026-06-15
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_problem_solver"
down_revision = "0005_ncert_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "problem_solver_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("notebook_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("notebooks.id"), nullable=False),
        sa.Column("problem_text", sa.Text(), nullable=True),
        sa.Column("problem_text_normalized", sa.Text(), nullable=True),
        sa.Column("input_type", sa.String(), nullable=False, server_default="text"),
        sa.Column("source_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("problem_dna", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("solving_mode", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=False, server_default="created"),
        sa.Column("interaction_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expert_solution", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("trace_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_problem_solver_sessions_tenant_id", "problem_solver_sessions", ["tenant_id"])
    op.create_index("ix_problem_solver_sessions_user_id", "problem_solver_sessions", ["user_id"])
    op.create_index("ix_problem_solver_sessions_notebook_id", "problem_solver_sessions", ["notebook_id"])

    op.create_table(
        "problem_solver_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("problem_solver_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_type", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_problem_solver_steps_session_id", "problem_solver_steps", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_problem_solver_steps_session_id", table_name="problem_solver_steps")
    op.drop_table("problem_solver_steps")
    op.drop_index("ix_problem_solver_sessions_notebook_id", table_name="problem_solver_sessions")
    op.drop_index("ix_problem_solver_sessions_user_id", table_name="problem_solver_sessions")
    op.drop_index("ix_problem_solver_sessions_tenant_id", table_name="problem_solver_sessions")
    op.drop_table("problem_solver_sessions")
