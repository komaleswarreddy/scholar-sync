"""IIL foundation — concepts, interaction logs, feedback, expertise tier

Revision ID: 0009_iil_foundation
Revises: 0008_user_credentials
"""

from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009_iil_foundation"
down_revision = "0008_user_credentials"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "concepts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("board", sa.String(), nullable=False, server_default="CBSE"),
        sa.Column("class_num", sa.SmallInteger(), nullable=False),
        sa.Column("subject_key", sa.String(), nullable=False),
        sa.Column("chapter_no", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("ncert_chapter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ncert_catalog_chapters.id", ondelete="SET NULL"), nullable=True),
        sa.Column("parent_concept_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("board", "class_num", "subject_key", "chapter_no", "slug", name="uq_concepts_board_class_subject_chapter_slug"),
    )
    op.create_index("ix_concepts_board", "concepts", ["board"])
    op.create_index("ix_concepts_class_num", "concepts", ["class_num"])
    op.create_index("ix_concepts_subject_key", "concepts", ["subject_key"])
    op.create_index("ix_concepts_slug", "concepts", ["slug"])
    op.create_index("ix_concepts_tenant_id", "concepts", ["tenant_id"])

    op.add_column("users", sa.Column("expertise_tier", sa.String(), nullable=True))
    op.execute(
        """
        UPDATE users SET expertise_tier = CASE
            WHEN role = 'teacher' THEN 'teacher'
            WHEN role = 'expert' THEN 'sme'
            ELSE 'student'
        END
        WHERE expertise_tier IS NULL
        """
    )
    op.alter_column("users", "expertise_tier", nullable=False, server_default="student")

    op.create_table(
        "interaction_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=True),
        sa.Column("problem_solver_step_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("problem_solver_steps.id", ondelete="CASCADE"), nullable=True),
        sa.Column("chat_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chats.id", ondelete="CASCADE"), nullable=True),
        sa.Column("notebook_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("notebooks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("user_tier", sa.String(), nullable=False, server_default="student"),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("query_intent", sa.String(), nullable=True),
        sa.Column("concept_node_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("conversation_position", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_followup", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("chain_depth", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("chunks_retrieved", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("retrieval_strategy", sa.String(), nullable=True),
        sa.Column("kb_hit", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("derived_hit", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("fallback_triggered", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("response_token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("citations_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("grounding_mode", sa.String(), nullable=False, server_default="strict"),
        sa.Column("out_of_kb_indicator", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("message_id", name="uq_interaction_logs_message_id"),
    )
    op.create_index("ix_interaction_logs_tenant_created", "interaction_logs", ["tenant_id", "created_at"])
    op.create_index("ix_interaction_logs_concept_tier_created", "interaction_logs", ["concept_node_id", "user_tier", "created_at"])
    op.create_index("ix_interaction_logs_chat_position", "interaction_logs", ["chat_id", "conversation_position"])
    op.create_index("ix_interaction_logs_tier_depth_created", "interaction_logs", ["user_tier", "chain_depth", "created_at"])
    op.create_index("ix_interaction_logs_notebook_id", "interaction_logs", ["notebook_id"])

    op.create_table(
        "interaction_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=True),
        sa.Column("problem_solver_step_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("problem_solver_steps.id", ondelete="CASCADE"), nullable=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("user_tier", sa.String(), nullable=False),
        sa.Column("signal_type", sa.String(), nullable=False),
        sa.Column("concept_node_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("dimension_tag", sa.String(), nullable=True),
        sa.Column("free_text", sa.Text(), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_ifb_message_signal", "interaction_feedback", ["message_id", "signal_type"])
    op.create_index("ix_ifb_concept_signal", "interaction_feedback", ["concept_node_id", "signal_type"])
    op.create_index("ix_ifb_tier_signal_created", "interaction_feedback", ["user_tier", "signal_type", "created_at"])
    op.create_index("ix_ifb_tenant_created", "interaction_feedback", ["tenant_id", "created_at"])

    # Backfill legacy thumbs feedback
    op.execute(
        """
        INSERT INTO interaction_feedback (
            id, message_id, user_id, user_tier, signal_type, free_text, tenant_id, created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            m.id,
            c.user_id,
            COALESCE(u.expertise_tier, 'student'),
            CASE WHEN m.feedback = 'thumbs_up' THEN 'helpful' ELSE 'not_helpful' END,
            m.feedback_reason,
            c.tenant_id,
            COALESCE(m.created_at, NOW()),
            NOW()
        FROM messages m
        JOIN chats c ON c.id = m.chat_id
        LEFT JOIN users u ON u.id::text = c.user_id OR u.clerk_user_id = c.user_id
        WHERE m.feedback IN ('thumbs_up', 'thumbs_down')
        """
    )

    op.drop_column("messages", "feedback_reason")
    op.drop_column("messages", "feedback")

    op.create_table(
        "problem_solver_session_chats",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("problem_solver_sessions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("chat_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("problem_solver_session_chats")
    op.add_column("messages", sa.Column("feedback", sa.String(), nullable=True))
    op.add_column("messages", sa.Column("feedback_reason", sa.Text(), nullable=True))
    op.execute(
        """
        UPDATE messages m SET
            feedback = CASE WHEN f.signal_type = 'helpful' THEN 'thumbs_up' WHEN f.signal_type = 'not_helpful' THEN 'thumbs_down' END,
            feedback_reason = f.free_text
        FROM interaction_feedback f
        WHERE f.message_id = m.id AND f.signal_type IN ('helpful', 'not_helpful')
        """
    )
    op.drop_table("interaction_feedback")
    op.drop_table("interaction_logs")
    op.drop_column("users", "expertise_tier")
    op.drop_table("concepts")
