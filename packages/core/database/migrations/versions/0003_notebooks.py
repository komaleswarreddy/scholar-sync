"""notebooks entity and notebook_id linkage

Revision ID: 0003_notebooks
Revises: 0002_ncert_global_knowledge
Create Date: 2026-06-05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

revision = "0003_notebooks"
down_revision = "0002_ncert_global_knowledge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notebooks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False, server_default="Untitled notebook"),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("mode", sa.String(), nullable=False, server_default="exploratory"),
        sa.Column("subtitle", sa.String(), nullable=True),
        sa.Column("subject", sa.String(), nullable=True),
        sa.Column("class_level", sa.String(), nullable=True),
        sa.Column("focus", sa.String(), nullable=True),
        sa.Column("mastery_percent", sa.Integer(), nullable=True),
        sa.Column("settings", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("last_studied_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_notebooks_tenant_id", "notebooks", ["tenant_id"], unique=False)
    op.create_index("ix_notebooks_user_id", "notebooks", ["user_id"], unique=False)
    op.create_index("ix_notebooks_slug", "notebooks", ["slug"], unique=False)
    op.create_index(
        "ix_notebooks_tenant_user_slug",
        "notebooks",
        ["tenant_id", "user_id", "slug"],
        unique=True,
    )

    op.add_column(
        "sources",
        sa.Column("notebook_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_sources_notebook_id",
        "sources",
        "notebooks",
        ["notebook_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_sources_notebook_id", "sources", ["notebook_id"], unique=False)

    op.add_column(
        "chats",
        sa.Column("notebook_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_chats_notebook_id",
        "chats",
        "notebooks",
        ["notebook_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_chats_notebook_id", "chats", ["notebook_id"], unique=False)

    op.add_column(
        "notes",
        sa.Column("notebook_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_notes_notebook_id",
        "notes",
        "notebooks",
        ["notebook_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_notes_notebook_id", "notes", ["notebook_id"], unique=False)

    # Backfill: one default notebook per (tenant_id, user_id) with existing data
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            """
            SELECT DISTINCT tenant_id::text AS tenant_id, user_id
            FROM (
                SELECT tenant_id, user_id FROM sources
                UNION
                SELECT tenant_id, user_id FROM chats
                UNION
                SELECT tenant_id, user_id FROM notes
            ) AS users_with_data
            """
        )
    ).fetchall()

    for row in rows:
        tenant_id = row[0]
        user_id = row[1]
        notebook_id = str(uuid.uuid4())
        slug = f"default-{notebook_id[:8]}"
        conn.execute(
            sa.text(
                """
                INSERT INTO notebooks (id, tenant_id, user_id, title, slug, mode)
                VALUES (:id, :tenant_id, :user_id, :title, :slug, :mode)
                """
            ),
            {
                "id": notebook_id,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "title": "My Workspace",
                "slug": slug,
                "mode": "exploratory",
            },
        )
        conn.execute(
            sa.text(
                """
                UPDATE sources SET notebook_id = :notebook_id
                WHERE tenant_id = :tenant_id AND user_id = :user_id AND notebook_id IS NULL
                """
            ),
            {"notebook_id": notebook_id, "tenant_id": tenant_id, "user_id": user_id},
        )
        conn.execute(
            sa.text(
                """
                UPDATE chats SET notebook_id = :notebook_id
                WHERE tenant_id = :tenant_id AND user_id = :user_id AND notebook_id IS NULL
                """
            ),
            {"notebook_id": notebook_id, "tenant_id": tenant_id, "user_id": user_id},
        )
        conn.execute(
            sa.text(
                """
                UPDATE notes SET notebook_id = :notebook_id
                WHERE tenant_id = :tenant_id AND user_id = :user_id AND notebook_id IS NULL
                """
            ),
            {"notebook_id": notebook_id, "tenant_id": tenant_id, "user_id": user_id},
        )

    op.execute("ALTER TABLE public.notebooks ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.notebooks FORCE ROW LEVEL SECURITY;")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE public.notebooks FROM anon, authenticated;")


def downgrade() -> None:
    op.drop_index("ix_notes_notebook_id", table_name="notes")
    op.drop_constraint("fk_notes_notebook_id", "notes", type_="foreignkey")
    op.drop_column("notes", "notebook_id")

    op.drop_index("ix_chats_notebook_id", table_name="chats")
    op.drop_constraint("fk_chats_notebook_id", "chats", type_="foreignkey")
    op.drop_column("chats", "notebook_id")

    op.drop_index("ix_sources_notebook_id", table_name="sources")
    op.drop_constraint("fk_sources_notebook_id", "sources", type_="foreignkey")
    op.drop_column("sources", "notebook_id")

    op.drop_index("ix_notebooks_tenant_user_slug", table_name="notebooks")
    op.drop_index("ix_notebooks_slug", table_name="notebooks")
    op.drop_index("ix_notebooks_user_id", table_name="notebooks")
    op.drop_index("ix_notebooks_tenant_id", table_name="notebooks")
    op.drop_table("notebooks")
