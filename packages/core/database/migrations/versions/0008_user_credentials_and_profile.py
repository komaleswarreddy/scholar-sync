"""user credentials and profile fields

Revision ID: 0008_user_credentials
Revises: 0007_source_questions
Create Date: 2026-07-03
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_user_credentials"
down_revision = "0007_source_questions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop global unique on email (email becomes optional)
    op.drop_index("ix_users_email", table_name="users")
    op.create_index("ix_users_email", "users", ["email"], unique=False)

    op.add_column(
        "users",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("users", sa.Column("username", sa.String(), nullable=True))
    op.add_column("users", sa.Column("password_hash", sa.String(), nullable=True))
    op.add_column("users", sa.Column("first_name", sa.String(), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(), nullable=True))
    op.add_column("users", sa.Column("mobile", sa.String(), nullable=True))
    op.add_column("users", sa.Column("institute", sa.String(), nullable=True))
    op.add_column("users", sa.Column("class_level", sa.String(), nullable=True))
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )

    op.create_foreign_key(
        "fk_users_tenant_id",
        "users",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"], unique=False)
    op.create_index("ix_users_username", "users", ["username"], unique=False)
    op.create_unique_constraint("uq_users_tenant_username", "users", ["tenant_id", "username"])

    # Migrate legacy role values
    op.execute("UPDATE users SET role = 'student' WHERE role = 'user'")
    op.execute("UPDATE users SET role = 'schooladmin' WHERE role = 'admin'")

    # Make email nullable for legacy rows without email
    op.alter_column("users", "email", existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    op.drop_constraint("uq_users_tenant_username", "users", type_="unique")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_constraint("fk_users_tenant_id", "users", type_="foreignkey")
    op.drop_column("users", "is_active")
    op.drop_column("users", "class_level")
    op.drop_column("users", "institute")
    op.drop_column("users", "mobile")
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "username")
    op.drop_column("users", "tenant_id")

    op.execute("UPDATE users SET role = 'user' WHERE role = 'student'")
    op.execute("UPDATE users SET role = 'admin' WHERE role = 'schooladmin'")

    op.alter_column("users", "email", existing_type=sa.String(), nullable=False)
    op.drop_index("ix_users_email", table_name="users")
    op.create_index("ix_users_email", "users", ["email"], unique=True)
