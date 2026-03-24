from __future__ import annotations

import asyncio
import uuid
from typing import Dict, Any, Optional, List
import sys
from pathlib import Path

import httpx
from sqlalchemy import select

# Ensure project root is importable when running as a script.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings
from packages.core.database.connection import AsyncSessionLocal
from packages.core.database.models.user import User


def _extract_primary_email(clerk_user: Dict[str, Any]) -> Optional[str]:
    email_addresses = clerk_user.get("email_addresses", []) or []
    if not email_addresses:
        return None
    verified_email = next(
        (e.get("email_address") for e in email_addresses if (e.get("verification") or {}).get("status") == "verified"),
        None,
    )
    email = verified_email or email_addresses[0].get("email_address")
    if not email:
        return None
    return str(email).strip().lower()


async def _fetch_all_clerk_users() -> List[Dict[str, Any]]:
    if not settings.CLERK_SECRET_KEY:
        return []
    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}",
            "Content-Type": "application/json",
        }
        all_clerk_users: List[Dict[str, Any]] = []
        limit = 500
        offset = 0
        while True:
            response = await client.get(
                "https://api.clerk.com/v1/users",
                headers=headers,
                params={"limit": limit, "offset": offset},
                timeout=30.0,
            )
            if response.status_code != 200:
                raise RuntimeError(f"Clerk API error: {response.status_code} {response.text[:200]}")
            data = response.json()
            if isinstance(data, list):
                users_page = data
                total_count = None
            elif isinstance(data, dict):
                users_page = data.get("data", [])
                total_count = data.get("total_count")
            else:
                users_page = []
                total_count = None
            if not users_page:
                break
            all_clerk_users.extend(users_page)
            if total_count is not None and len(all_clerk_users) >= int(total_count):
                break
            if len(users_page) < limit:
                break
            offset += limit
        return all_clerk_users


async def run_backfill() -> None:
    clerk_users = await _fetch_all_clerk_users()
    if not clerk_users:
        print("[BACKFILL] No users returned by Clerk.")
        return

    inserted = 0
    updated = 0
    email_fixed = 0
    skipped_no_email = 0

    async with AsyncSessionLocal() as db:
        existing_res = await db.execute(select(User))
        existing = existing_res.scalars().all()
        by_clerk: Dict[str, User] = {u.clerk_user_id: u for u in existing if u.clerk_user_id}
        by_email: Dict[str, User] = {str(u.email).strip().lower(): u for u in existing if u.email}

        for cu in clerk_users:
            clerk_user_id = str(cu.get("id") or "").strip()
            email = _extract_primary_email(cu)
            if not email:
                skipped_no_email += 1
                continue

            row = by_clerk.get(clerk_user_id) if clerk_user_id else None
            if row is None:
                row = by_email.get(email)

            if row is None:
                row = User(
                    id=uuid.uuid4(),
                    email=email,
                    clerk_user_id=clerk_user_id or None,
                    role="user",
                )
                db.add(row)
                inserted += 1
                if clerk_user_id:
                    by_clerk[clerk_user_id] = row
                by_email[email] = row
                continue

            changed = False
            if clerk_user_id and not row.clerk_user_id:
                row.clerk_user_id = clerk_user_id
                changed = True

            existing_email = str(row.email or "").strip().lower()
            is_placeholder = (
                "{{" in existing_email
                or "}}" in existing_email
                or "user.primary_email_address" in existing_email
            )
            if (not existing_email or is_placeholder) and email:
                row.email = email
                changed = True
                email_fixed += 1

            if changed:
                updated += 1
            if clerk_user_id:
                by_clerk[clerk_user_id] = row
            by_email[email] = row

        await db.commit()

    print(
        "[BACKFILL] Completed "
        f"clerk_total={len(clerk_users)} inserted={inserted} "
        f"updated={updated} email_fixed={email_fixed} skipped_no_email={skipped_no_email}"
    )


if __name__ == "__main__":
    asyncio.run(run_backfill())
