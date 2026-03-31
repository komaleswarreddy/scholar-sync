from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

from sqlalchemy import select

# Ensure repo root is on sys.path when running `python scripts/seed_db.py`
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.core.database.connection import AsyncSessionLocal, engine
from packages.core.database.models.tenant import Tenant

async def seed_tenant():
    print("Seeding database...")
    async with AsyncSessionLocal() as session:
        # Check if the dev tenant already exists
        dev_id = "eeff7c1c-fe22-4573-ad93-a36f19ad4dc5"
        result = await session.execute(
            select(Tenant).where(Tenant.subdomain == "default")
        )
        existing_tenant = result.scalar_one_or_none()

        if not existing_tenant:
            new_tenant = Tenant(
                id=uuid.UUID(dev_id),
                subdomain="default",
                name="Development School",
                settings={"theme": "light"}
            )
            session.add(new_tenant)
            await session.commit()
            print(f"Created 'default' tenant with ID: {dev_id}")
        else:
            print(f"Tenant 'default' already exists with ID: {existing_tenant.id}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_tenant())