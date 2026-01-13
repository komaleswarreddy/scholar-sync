# app/core/middleware.py
from fastapi import Request, HTTPException, status
from typing import Callable
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
    """
    Middleware to:
    1️⃣ Ignore internal / OPTIONS / excluded paths
    2️⃣ Resolve tenant from subdomain
    3️⃣ Extract user_id from X-User-ID header or Clerk JWT
    4️⃣ Attach tenant_id and user_id to request.state
    5️⃣ Dev-friendly fallback for local testing
    """

    # 1️⃣ Ignore Chrome/internal requests
    if request.url.path.startswith("/.well-known") or request.method == "OPTIONS" or request.url.path in EXCLUDED_PATHS:
        return await call_next(request)

    # 2️⃣ Extract tenant from subdomain
    host = request.headers.get("host", "")
    subdomain = host.split(".")[0] if "." in host else "default"

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Tenant).where(Tenant.subdomain == subdomain))
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid tenant")

    request.state.tenant_id = str(tenant.id)

    # 3️⃣ Extract user_id
    user_id = request.headers.get("X-User-ID")

    # 4️⃣ If no X-User-ID, try JWT
    if not user_id:
        auth_header = request.headers.get("Authorization")
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
                if not user_id:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token (no user id)")
            except JWTError as e:
                print(f"JWT decode error: {str(e)}")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
        elif settings.ENVIRONMENT == "development":
            # 5️⃣ Dev fallback for local testing
            user_id = "dev-user-123"
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")

    # 6️⃣ Attach user_id to request
    request.state.user_id = user_id

    # 7️⃣ Continue request
    response = await call_next(request)
    return response
