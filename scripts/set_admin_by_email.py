from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.core.database.connection import AsyncSessionLocal
from packages.core.database.models.user import User


TARGET_EMAIL = "scombinator26@gmail.com"


async def main() -> None:
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).where(User.email == TARGET_EMAIL))
        user = res.scalar_one_or_none()
        if not user:
            print(f"[ADMIN] User not found for email: {TARGET_EMAIL}")
            return
        user.role = "admin"
        await db.commit()
        print(
            f"[ADMIN] Updated role to admin for {TARGET_EMAIL} "
            f"(clerk_user_id={user.clerk_user_id})"
        )


if __name__ == "__main__":
    asyncio.run(main())
