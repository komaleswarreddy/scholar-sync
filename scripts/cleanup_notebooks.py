"""Delete all notebooks and notes (dev/test reset)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import delete, func, select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.core.database.connection import AsyncSessionLocal, engine
from packages.core.database.models.note import Note
from packages.core.database.models.notebook import Notebook
from packages.core.database.models.studio_feature import StudioFeature


async def cleanup() -> None:
    try:
        async with AsyncSessionLocal() as session:
            nb_before = await session.scalar(select(func.count()).select_from(Notebook)) or 0
            notes_before = await session.scalar(select(func.count()).select_from(Note)) or 0
            studio_before = await session.scalar(select(func.count()).select_from(StudioFeature)) or 0

            print(
                f"Before cleanup: {nb_before} notebooks, {notes_before} notes, "
                f"{studio_before} studio assets"
            )

            result = await session.execute(select(Notebook))
            notebooks = result.scalars().all()
            for notebook in notebooks:
                await session.delete(notebook)

            await session.flush()
            await session.execute(delete(Note))
            await session.execute(delete(StudioFeature))
            await session.commit()

            nb_after = await session.scalar(select(func.count()).select_from(Notebook)) or 0
            notes_after = await session.scalar(select(func.count()).select_from(Note)) or 0
            studio_after = await session.scalar(select(func.count()).select_from(StudioFeature)) or 0

            print(
                f"After cleanup: {nb_after} notebooks, {notes_after} notes, "
                f"{studio_after} studio assets"
            )
            print("Done. Refresh the library/home page in your browser.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(cleanup())
