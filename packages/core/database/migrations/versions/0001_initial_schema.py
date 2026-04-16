"""initial schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-03-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Helpful on Supabase / Postgres for gen_random_uuid() (even though models default uuid4 in app)
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("subdomain", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("settings", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_tenants_subdomain", "tenants", ["subdomain"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("clerk_user_id", sa.String(), nullable=True),
        sa.Column("role", sa.String(), nullable=False, server_default="user"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_clerk_user_id", "users", ["clerk_user_id"], unique=False)

    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("s3_key", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False, server_default="pdf"),
        sa.Column("status", sa.String(), nullable=False, server_default="processing"),
        sa.Column("chunks_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_sources_tenant_id", "sources", ["tenant_id"], unique=False)
    op.create_index("ix_sources_user_id", "sources", ["user_id"], unique=False)

    op.create_table(
        "chats",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_chats_tenant_id", "chats", ["tenant_id"], unique=False)
    op.create_index("ix_chats_user_id", "chats", ["user_id"], unique=False)

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("chat_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chats.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=True),
        sa.Column("feedback", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_messages_chat_id", "messages", ["chat_id"], unique=False)

    op.create_table(
        "notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_ref_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_notes_tenant_id", "notes", ["tenant_id"], unique=False)
    op.create_index("ix_notes_user_id", "notes", ["user_id"], unique=False)

    op.create_table(
        "guardrail_user_blocks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("user_name", sa.String(), nullable=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("block_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("block_reason", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_guardrail_user_blocks_tenant_id", "guardrail_user_blocks", ["tenant_id"], unique=False)
    op.create_index("ix_guardrail_user_blocks_user_id", "guardrail_user_blocks", ["user_id"], unique=False)
    op.create_index("ix_guardrail_user_blocks_session_id", "guardrail_user_blocks", ["session_id"], unique=False)
    op.create_index("ix_guardrail_user_blocks_created_at", "guardrail_user_blocks", ["created_at"], unique=False)

    op.create_table(
        "alert_user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("alert_type", sa.String(), nullable=False),
        sa.Column("alert_message", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(), nullable=False, server_default="medium"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_alert_user_sessions_tenant_id", "alert_user_sessions", ["tenant_id"], unique=False)
    op.create_index("ix_alert_user_sessions_user_id", "alert_user_sessions", ["user_id"], unique=False)
    op.create_index("ix_alert_user_sessions_session_id", "alert_user_sessions", ["session_id"], unique=False)
    op.create_index("ix_alert_user_sessions_alert_type", "alert_user_sessions", ["alert_type"], unique=False)
    op.create_index("ix_alert_user_sessions_created_at", "alert_user_sessions", ["created_at"], unique=False)

    # --------------------------
    # Supabase security baseline
    # --------------------------
    # This repo uses FastAPI + SQLAlchemy for DB access (not Supabase PostgREST from the browser).
    # On Supabase, tables in the `public` schema can be exposed via PostgREST, so we lock them down:
    # - Enable RLS (deny-by-default unless explicit policies exist)
    # - Revoke all table privileges from `anon` and `authenticated`
    # - Remove default privileges so future tables don't auto-grant to those roles
    op.execute("ALTER TABLE public.tenants ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.sources ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.chats ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.notes ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.guardrail_user_blocks ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.alert_user_sessions ENABLE ROW LEVEL SECURITY;")

    # FORCE RLS is optional but recommended; it prevents owners from bypassing RLS accidentally.
    op.execute("ALTER TABLE public.tenants FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.users FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.sources FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.chats FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.messages FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.notes FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.guardrail_user_blocks FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.alert_user_sessions FORCE ROW LEVEL SECURITY;")

    op.execute("REVOKE ALL PRIVILEGES ON TABLE public.tenants FROM anon, authenticated;")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE public.users FROM anon, authenticated;")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE public.sources FROM anon, authenticated;")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE public.chats FROM anon, authenticated;")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE public.messages FROM anon, authenticated;")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE public.notes FROM anon, authenticated;")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE public.guardrail_user_blocks FROM anon, authenticated;")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE public.alert_user_sessions FROM anon, authenticated;")

    # Prevent future tables in public from inheriting unsafe grants.
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated;")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated;")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON FUNCTIONS FROM anon, authenticated;")


def downgrade() -> None:
    op.drop_index("ix_alert_user_sessions_created_at", table_name="alert_user_sessions")
    op.drop_index("ix_alert_user_sessions_alert_type", table_name="alert_user_sessions")
    op.drop_index("ix_alert_user_sessions_session_id", table_name="alert_user_sessions")
    op.drop_index("ix_alert_user_sessions_user_id", table_name="alert_user_sessions")
    op.drop_index("ix_alert_user_sessions_tenant_id", table_name="alert_user_sessions")
    op.drop_table("alert_user_sessions")

    op.drop_index("ix_guardrail_user_blocks_created_at", table_name="guardrail_user_blocks")
    op.drop_index("ix_guardrail_user_blocks_session_id", table_name="guardrail_user_blocks")
    op.drop_index("ix_guardrail_user_blocks_user_id", table_name="guardrail_user_blocks")
    op.drop_index("ix_guardrail_user_blocks_tenant_id", table_name="guardrail_user_blocks")
    op.drop_table("guardrail_user_blocks")

    op.drop_index("ix_notes_user_id", table_name="notes")
    op.drop_index("ix_notes_tenant_id", table_name="notes")
    op.drop_table("notes")

    op.drop_index("ix_messages_chat_id", table_name="messages")
    op.drop_table("messages")

    op.drop_index("ix_chats_user_id", table_name="chats")
    op.drop_index("ix_chats_tenant_id", table_name="chats")
    op.drop_table("chats")

    op.drop_index("ix_sources_user_id", table_name="sources")
    op.drop_index("ix_sources_tenant_id", table_name="sources")
    op.drop_table("sources")

    op.drop_index("ix_users_clerk_user_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    op.drop_index("ix_tenants_subdomain", table_name="tenants")
    op.drop_table("tenants")

