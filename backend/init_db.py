import asyncio

# IMPORTANT: import models BEFORE create_all
import app.models  # <-- THIS LINE MATTERS

from app.core.database import engine, Base


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ All tables created successfully!")


if __name__ == "__main__":
    asyncio.run(init_db())
