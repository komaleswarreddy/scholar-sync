"""Add feedback_reason to messages

Revision ID: 0004_message_feedback_reason
Revises: 0004_studio_features
Create Date: 2026-06-06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0004_message_feedback_reason"
down_revision = "0004_studio_features"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("feedback_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("messages", "feedback_reason")
