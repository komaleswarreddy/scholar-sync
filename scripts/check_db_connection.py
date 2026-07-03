"""Quick Supabase/PostgreSQL connectivity and schema check."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text

from config.settings import settings


def main() -> None:
    url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    engine = create_engine(url)
    with engine.connect() as conn:
        pg = conn.execute(text("SELECT version()")).scalar()
        print(f"PostgreSQL: {pg.split(',')[0]}")

        tenants = conn.execute(text("SELECT COUNT(*) FROM tenants")).scalar()
        print(f"tenants count: {tenants}")

        alembic = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        print(f"alembic revision: {alembic}")

        cols = conn.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'users'
                  AND column_name IN ('username', 'password_hash', 'tenant_id', 'is_active')
                ORDER BY column_name
                """
            )
        ).fetchall()
        print(f"users auth columns: {[r[0] for r in cols]}")


if __name__ == "__main__":
    main()
