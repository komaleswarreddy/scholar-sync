"""
Alembic environment for ScholarSync.

This repo uses SQLAlchemy Async in the app, but Alembic migrations run with a
sync engine for broad compatibility (psycopg2).
"""

from __future__ import annotations

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import make_url

from config.settings import settings
from packages.core.database.connection import Base

# Import models so Base.metadata is fully populated
from packages.core.database import models as _models  # noqa: F401

config = context.config

target_metadata = Base.metadata


def _sync_migration_url() -> str:
    """
    Convert app DATABASE_URL into a sync URL for Alembic.
    - postgresql+asyncpg://...  -> postgresql+psycopg2://...
    - postgresql://...          -> postgresql+psycopg2://...
    """
    raw = (settings.DATABASE_URL or "").strip()
    if not raw:
        return raw

    # Use SQLAlchemy URL parsing to correctly handle special characters in passwords
    # (e.g. '$', '@', ':'), and only then switch driver to psycopg2 for Alembic.
    u = make_url(raw)
    if u.drivername == "postgresql":
        u = u.set(drivername="postgresql+psycopg2")
    elif u.drivername == "postgresql+asyncpg":
        u = u.set(drivername="postgresql+psycopg2")

    # Render as string with password so Alembic can connect
    return u.render_as_string(hide_password=False)


def run_migrations_offline() -> None:
    url = _sync_migration_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    cfg = config.get_section(config.config_ini_section) or {}
    cfg["sqlalchemy.url"] = _sync_migration_url()

    connectable = engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

