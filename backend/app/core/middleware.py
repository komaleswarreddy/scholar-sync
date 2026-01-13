from fastapi import Request, HTTPException, status
from typing import Callable
import re
from jose import jwt, JWTError
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.core.config import settings

# Paths that don’t require authentication
EXCLUDED_PATHS = {
    "/",
    "/health",
    "/openapi.json",
    "/docs",
    "/docs/oauth2-redirect",
}

async def tenant_and_auth_middleware(request: Request, call_next: Callable):
    # 1️⃣ Ignore Chrome / browser internal requests
    if request.url.path.startswith("/.well-known") or request.method == "OPTIONS" or request.url.path in EXCLUDED_PATHS:
        return await call_next(request)

    # 2️⃣ Resolve tenant
    host = request.headers.get("host", "")
    subdomain = host.split(".")[0] if "." in host else "default"

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Tenant).where(Tenant.subdomain == subdomain)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid tenant",
            )

    request.state.tenant_id = str(tenant.id)

    # 3️⃣ Extract user ID from Authorization header (Clerk JWT)
    auth_header = request.headers.get("Authorization")
    user_id = None

    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "").strip()
        try:
            payload = jwt.decode(
                token,
                settings.CLERK_JWT_PUBLIC_KEY,
                algorithms=["RS256"],
                audience=settings.CLERK_JWT_AUDIENCE,
                issuer=settings.CLERK_JWT_ISSUER,
            )
            user_id = payload.get("sub")
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

    # 4️⃣ Temporary fallback user for testing
    if not user_id:
        user_id = "temp-dev-user"

    request.state.user_id = user_id

    response = await call_next(request)
    return response
