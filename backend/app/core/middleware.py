from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import re

from jose import jwt, JWTError
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.core.config import settings

# Clerk JWT
CLERK_JWT_SECRET = settings.CLERK_SECRET_KEY
CLERK_ALGORITHM = "RS256"

# Paths that should NOT require tenant lookup
EXCLUDED_PATHS = {
    "/",
    "/health",
    "/openapi.json",
    "/docs",
    "/redoc",
    "/api/docs",
    "/api/redoc",
}

async def tenant_middleware(request: Request, call_next: Callable):
    path = request.url.path

    # ------------------ Skip excluded paths ------------------
    if path in EXCLUDED_PATHS or path.startswith("/api/docs") or path.startswith("/api/redoc"):
        return await call_next(request)

    # ------------------ Extract tenant ------------------
    host = request.headers.get("host", "")

    # Local development handling
    if host.startswith("127.0.0.1") or host.startswith("localhost"):
        subdomain = request.headers.get("X-Tenant", "default")
    else:
        match = re.match(r"^([a-z0-9-]+)\.", host)
        subdomain = match.group(1) if match else "default"

    # Fetch tenant from DB
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Tenant).where(Tenant.subdomain == subdomain)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise HTTPException(
                status_code=404,
                detail=f"Tenant not found for subdomain: {subdomain}"
            )

        request.state.tenant_id = str(tenant.id)
        request.state.subdomain = subdomain

    # ------------------ Extract Clerk JWT ------------------
    auth_header = request.headers.get("Authorization")
    request.state.clerk_user_id = None

    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(
                token,
                CLERK_JWT_SECRET,
                algorithms=[CLERK_ALGORITHM],
                options={"verify_aud": False},
            )
            request.state.clerk_user_id = payload.get("sub")
        except JWTError:
            request.state.clerk_user_id = None

    return await call_next(request)
