"""Quick verification for tutor catalog seed."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.core.database.connection import AsyncSessionLocal, engine
from packages.core.services.tutor_catalog_service import TutorCatalogService


async def main() -> None:
    async with AsyncSessionLocal() as db:
        service = TutorCatalogService(db)
        for class_num in (12,):
            subjects = await service.list_subjects(class_num)
            print(f"Class {class_num}: {len(subjects)} subjects")
            if subjects:
                chapters = await service.list_chapters(class_num, subjects[0]["id"])
                print(f"  {subjects[0]['label']}: {len(chapters)} chapters")
                if chapters:
                    concepts = await service.list_concepts(
                        class_num, subjects[0]["id"], chapters[0]["chapter_no"]
                    )
                    print(f"  Ch.{chapters[0]['chapter_no']}: {len(concepts)} concept options")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
