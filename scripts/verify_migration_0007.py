#!/usr/bin/env python3
"""Quick check that migration 0007_source_questions applied."""

from __future__ import annotations

import asyncio

from sqlalchemy import text

from packages.core.database.connection import AsyncSessionLocal


async def main() -> None:
    async with AsyncSessionLocal() as db:
        r = await db.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'source_questions' ORDER BY ordinal_position"
            )
        )
        cols = [row[0] for row in r.fetchall()]
        r2 = await db.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'sources' AND column_name = 'source_metadata'"
            )
        )
        has_meta = r2.fetchone() is not None
    print("source_questions table:", "OK" if cols else "MISSING")
    print("columns:", ", ".join(cols) if cols else "none")
    print("sources.source_metadata:", "OK" if has_meta else "MISSING")
    if not cols or not has_meta:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
