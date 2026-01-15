import asyncio
import uuid
from app.core.database import AsyncSessionLocal, engine
from app.models.tenant import Tenant
from sqlalchemy import select

async def seed_tenant():
    print("🌱 Seeding database...")
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
            print(f"✅ Created 'default' tenant with ID: {dev_id}")
        else:
            print(f"ℹ️ Tenant 'default' already exists with ID: {existing_tenant.id}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_tenant())