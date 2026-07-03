"""
Tenant Middleware

Handles tenant extraction from subdomain and authentication.
Sets tenant_id and user_id in request state.
"""

from fastapi import Request, HTTPException
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Scope, Receive, Send
from sqlalchemy import select
import logging
import re
import traceback
import time

from packages.core.database.connection import AsyncSessionLocal
from packages.core.database.models.tenant import Tenant
from apps.api.middleware.auth import (
    extract_platform_user_id,
    extract_platform_role,
    extract_admin_portal_user_id,
    extract_teacher_portal_user_id,
)
from apps.api.middleware.common import add_cors_headers
from config.settings import settings

logger = logging.getLogger("scholarsync.tenant")


def _redact(user_id) -> str:
    """Redact a user id for logs: keep a short non-reversible hint only."""
    if not user_id:
        return "<none>"
    s = str(user_id)
    return f"{s[:4]}…{s[-2:]}" if len(s) > 8 else "<redacted>"

# Configuration for Development
DEV_TENANT_ID = "eeff7c1c-fe22-4573-ad93-a36f19ad4dc5"
EXCLUDED_PATHS = {
    "/",
    "/health",
    "/health/langsmith",
    "/openapi.json",
    "/docs",
    "/api/docs",
    "/api/redoc",
    "/favicon.ico",
    "/.well-known",
    "/metrics",
}

# Cache subdomain -> tenant_id to avoid a DB round-trip on every API request (dashboard fires many in parallel)
_TENANT_CACHE_TTL_SEC = 300.0
_tenant_id_by_subdomain: dict[str, tuple[str, float]] = {}


async def warm_tenant_cache() -> None:
    """Preload default tenant so first login/API call avoids a cold DB lookup."""
    now = time.monotonic()
    if "default" in _tenant_id_by_subdomain:
        return
    if settings.ENVIRONMENT == "development":
        _tenant_id_by_subdomain["default"] = (DEV_TENANT_ID, now + _TENANT_CACHE_TTL_SEC)
        logger.info("Tenant cache warmed (dev default -> %s)", DEV_TENANT_ID)
        return
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Tenant).where(Tenant.subdomain == "default"))
            tenant = result.scalar_one_or_none()
            if tenant:
                _tenant_id_by_subdomain["default"] = (str(tenant.id), now + _TENANT_CACHE_TTL_SEC)
                logger.info("Tenant cache warmed (default -> %s)", tenant.id)
    except Exception:
        logger.exception("Tenant cache warm-up failed")


def _resolve_dev_default_tenant(now: float) -> str | None:
    """Skip DB round-trip for localhost default tenant in development."""
    if settings.ENVIRONMENT != "development":
        return None
    _tenant_id_by_subdomain["default"] = (DEV_TENANT_ID, now + _TENANT_CACHE_TTL_SEC)
    return DEV_TENANT_ID


def _extract_auth_from_token(token: str) -> tuple[str | None, str | None]:
    """Resolve user_id and role from Bearer token (platform preferred)."""
    if not token:
        return None, None

    platform_user_id = extract_platform_user_id(token)
    if platform_user_id:
        return platform_user_id, extract_platform_role(token)

    admin_user_id = extract_admin_portal_user_id(token)
    if admin_user_id:
        return admin_user_id, "schooladmin"

    teacher_user_id = extract_teacher_portal_user_id(token)
    if teacher_user_id:
        return teacher_user_id, "teacher"

    return None, None

# Paths that require tenant but not user authentication (development only)
# These paths can work with just tenant_id from subdomain, no JWT required
TENANT_ONLY_PATHS = {"/api/v1/metrics", "/api/v1/dashboards", "/api/v1/alerts", "/debug"}

# Portal logins — tenant required, Bearer token not required
PUBLIC_AUTH_PATHS = {
    "/api/v1/admin/auth/login",
    "/api/v1/teacher/auth/login",
    "/api/v1/auth/login",
}


class TenantMiddleware:
    """
    Middleware for tenant isolation and authentication.
    
    Process:
    1. Extract subdomain from host header
    2. Lookup tenant in database
    3. Extract user_id from JWT token
    4. Set tenant_id and user_id in request state
    """
    
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        # Only process HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Create a request object from the scope to keep your logic working
        request = Request(scope, receive)

        try:
            # Initialize request state
            request.state.tenant_id = None
            request.state.user_id = None
            request.state.user_role = None

            # Step 1: Check if path is excluded OR if it's a CORS preflight request
            current_path = request.url.path
            method = request.method
            if settings.ENVIRONMENT != "development":
                logger.debug("%s %s", method, current_path)
            
            is_excluded = (
                current_path == "/" or 
                any(current_path.startswith(p) for p in EXCLUDED_PATHS if p != "/")
            )
            
            # Skip middleware for OPTIONS requests
            if request.method == "OPTIONS":
                await self.app(scope, receive, send)
                return

            if is_excluded:
                await self.app(scope, receive, send)
                return

            # Step 2: Extract subdomain from host header
            host = request.headers.get("host", "").lower()
            is_local = any(h in host for h in ["localhost", "127.0.0.1", "0.0.0.0", "testserver"])
            
            subdomain = "default"
            if not is_local and host:
                subdomain_match = re.match(r"^(?P<subdomain>.+?)\.scholarsync\.com", host)
                if subdomain_match:
                    subdomain = subdomain_match.group("subdomain")
                else:
                    raise HTTPException(status_code=403, detail="Invalid Host Header")

            # Step 3: Resolve tenant (cached; dev default skips DB)
            tenant_id = None
            now = time.monotonic()
            if subdomain == "default":
                tenant_id = _resolve_dev_default_tenant(now)

            cached = _tenant_id_by_subdomain.get(subdomain)
            if tenant_id is None and cached is not None:
                tid, exp = cached
                if exp > now:
                    tenant_id = tid

            if tenant_id is None:
                try:
                    async with AsyncSessionLocal() as db:
                        result = await db.execute(select(Tenant).where(Tenant.subdomain == subdomain))
                        tenant = result.scalar_one_or_none()

                        if tenant:
                            tenant_id = str(tenant.id)
                            _tenant_id_by_subdomain[subdomain] = (tenant_id, now + _TENANT_CACHE_TTL_SEC)
                            logger.info("Tenant found: %s -> %s", subdomain, tenant_id)
                        else:
                            if settings.ENVIRONMENT == "development":
                                logger.warning(
                                    "Tenant '%s' not found in DB, using fallback: %s",
                                    subdomain,
                                    DEV_TENANT_ID,
                                )
                                tenant_id = DEV_TENANT_ID
                                _tenant_id_by_subdomain[subdomain] = (tenant_id, now + _TENANT_CACHE_TTL_SEC)
                            else:
                                print(f"[ERROR] [MIDDLEWARE] 404: Tenant '{subdomain}' not found (production mode)")
                                origin = request.headers.get("Origin", "")
                                resp = JSONResponse(
                                    status_code=404,
                                    content={"detail": f"Organization '{subdomain}' not found."}
                                )
                                resp = add_cors_headers(resp, origin)
                                await resp(scope, receive, send)
                                return
                except Exception as db_error:
                    error_msg = str(db_error)
                    print(f"[ERROR] Database connection error: {error_msg}")
                    if settings.ENVIRONMENT == "development":
                        print(f"[WARNING] Database unavailable, using fallback tenant: {DEV_TENANT_ID}")
                        tenant_id = DEV_TENANT_ID
                        _tenant_id_by_subdomain[subdomain] = (tenant_id, now + _TENANT_CACHE_TTL_SEC)
                    else:
                        origin = request.headers.get("Origin", "")
                        resp = JSONResponse(
                            status_code=503,
                            content={"detail": "Database unavailable. Please try again later."}
                        )
                        resp = add_cors_headers(resp, origin)
                        await resp(scope, receive, send)
                        return

            # Set tenant_id in request state
            request.state.tenant_id = tenant_id

            # Extract origin early for CORS headers
            origin = request.headers.get("Origin", "")

            if current_path in PUBLIC_AUTH_PATHS:
                request.state.user_id = None
                request.state.user_role = None
                await self.app(scope, receive, send)
                return

            # Step 4: Extract user_id from Authorization header
            auth_header = request.headers.get("Authorization", "")
            user_id = None
            user_role = None
            
            # Check if this is a tenant-only path (metrics/dashboards in development)
            # BUT we still want to extract user_id if available for proper filtering
            is_tenant_only_path = (
                settings.ENVIRONMENT == "development" and
                any(current_path.startswith(path) for path in TENANT_ONLY_PATHS)
            )
            
            # For tenant-only paths in development, try to extract user_id but don't require it
            if is_tenant_only_path:
                logger.debug("Tenant-only path %s — best-effort user extraction", current_path)
                # Try to extract user_id if token is provided, but don't fail if it's missing
                if auth_header and auth_header.startswith("Bearer "):
                    token = auth_header.replace("Bearer ", "").strip()
                    if token:
                        user_id, user_role = _extract_auth_from_token(token)

                request.state.user_id = user_id
                request.state.user_role = user_role
                await self.app(scope, receive, send)
                return
            
            if not auth_header or not auth_header.startswith("Bearer "):
                resp = JSONResponse(
                    status_code=401,
                    content={
                        "detail": "Authentication required. Please provide a valid Bearer token in the Authorization header.",
                        "error_code": "MISSING_TOKEN"
                    }
                )
                resp = add_cors_headers(resp, origin)
                await resp(scope, receive, send)
                return
            
            token = auth_header.replace("Bearer ", "").strip()
            if not token:
                resp = JSONResponse(
                    status_code=401,
                    content={
                        "detail": "Invalid authentication token. Token cannot be empty.",
                        "error_code": "EMPTY_TOKEN"
                    }
                )
                resp = add_cors_headers(resp, origin)
                await resp(scope, receive, send)
                return
            
            try:
                user_id, user_role = _extract_auth_from_token(token)
                if user_id:
                    logger.info("Authenticated user: %s role=%s", _redact(user_id), user_role)
                else:
                    raise HTTPException(status_code=401, detail="Invalid token")
            except HTTPException:
                logger.info("Token verification failed for %s %s", method, current_path)
                resp = JSONResponse(
                    status_code=401,
                    content={
                        "detail": "Invalid or expired authentication token.",
                        "error_code": "INVALID_TOKEN"
                    }
                )
                resp = add_cors_headers(resp, origin)
                await resp(scope, receive, send)
                return
            except Exception:
                logger.exception("Error extracting user from token")
                resp = JSONResponse(
                    status_code=401,
                    content={
                        "detail": "Authentication error. Could not validate credentials.",
                        "error_code": "AUTH_ERROR"
                    }
                )
                resp = add_cors_headers(resp, origin)
                await resp(scope, receive, send)
                return
            
            # Step 5: Set user_id
            if not user_id:
                resp = JSONResponse(
                    status_code=401,
                    content={
                        "detail": "Authentication failed. User ID could not be extracted from token.",
                        "error_code": "MISSING_USER_ID"
                    }
                )
                resp = add_cors_headers(resp, origin)
                await resp(scope, receive, send)
                return
            
            request.state.user_id = user_id
            request.state.user_role = user_role

            await self.app(scope, receive, send)

        except Exception:
            logger.exception("Unhandled error in TenantMiddleware")
            origin = request.headers.get("Origin", "") if 'request' in locals() else None
            resp = JSONResponse(
                status_code=500,
                content={"detail": "Internal Server Error"}
            )
            resp = add_cors_headers(resp, origin)
            await resp(scope, receive, send)


