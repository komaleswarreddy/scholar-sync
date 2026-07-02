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
import uuid

from packages.core.database.connection import AsyncSessionLocal
from packages.core.database.models.tenant import Tenant
from packages.core.database.models.user import User
from apps.api.middleware.auth import (
    extract_user_id_from_token,
    extract_email_from_token,
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
_SYNCED_USERS_TTL_SEC = 600.0
_synced_user_ids: dict[str, float] = {}

# Paths that require tenant but not user authentication (development only)
# These paths can work with just tenant_id from subdomain, no JWT required
TENANT_ONLY_PATHS = {"/api/v1/metrics", "/api/v1/dashboards", "/api/v1/alerts", "/debug"}

# Portal logins — tenant required, Bearer token not required
PUBLIC_AUTH_PATHS = {"/api/v1/admin/auth/login", "/api/v1/teacher/auth/login"}


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

            # Step 1: Check if path is excluded OR if it's a CORS preflight request
            current_path = request.url.path
            method = request.method
            print(f"[MIDDLEWARE] {method} {current_path}")
            
            is_excluded = (
                current_path == "/" or 
                any(current_path.startswith(p) for p in EXCLUDED_PATHS if p != "/")
            )
            
            # Skip middleware for OPTIONS requests
            if request.method == "OPTIONS":
                print(f"[SKIP] [MIDDLEWARE] Skipping OPTIONS request")
                await self.app(scope, receive, send)
                return

            if is_excluded:
                print(f"[SKIP] [MIDDLEWARE] Path excluded: {current_path}")
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

            # Step 3: Database lookup for tenant (cached by subdomain)
            tenant_id = None
            now = time.monotonic()
            cached = _tenant_id_by_subdomain.get(subdomain)
            if cached is not None:
                tid, exp = cached
                if exp > now:
                    tenant_id = tid
                    print(f"[MIDDLEWARE] Tenant cache hit: {subdomain} -> {tenant_id}")

            if tenant_id is None:
                try:
                    async with AsyncSessionLocal() as db:
                        result = await db.execute(select(Tenant).where(Tenant.subdomain == subdomain))
                        tenant = result.scalar_one_or_none()

                        if tenant:
                            tenant_id = str(tenant.id)
                            _tenant_id_by_subdomain[subdomain] = (tenant_id, now + _TENANT_CACHE_TTL_SEC)
                            print(f"[SUCCESS] Tenant found: {subdomain} -> {tenant_id}")
                        else:
                            if settings.ENVIRONMENT == "development":
                                print(f"[WARNING] Tenant '{subdomain}' not found in DB, using fallback: {DEV_TENANT_ID}")
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
                await self.app(scope, receive, send)
                return

            # Step 4: Extract user_id from Authorization header
            auth_header = request.headers.get("Authorization", "")
            user_id = None
            
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
                        admin_user_id = extract_admin_portal_user_id(token)
                        teacher_user_id = None if admin_user_id else extract_teacher_portal_user_id(token)
                        if admin_user_id:
                            user_id = admin_user_id
                        elif teacher_user_id:
                            user_id = teacher_user_id
                        else:
                            try:
                                is_production = settings.ENVIRONMENT == "production"
                                user_id = extract_user_id_from_token(
                                    token,
                                    require_verification=is_production
                                )
                            except Exception:
                                logger.debug("Could not extract user_id for tenant-only path (non-fatal)")
                                user_id = None
                
                # Set user_id (may be None) and continue
                request.state.user_id = user_id
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
                admin_user_id = extract_admin_portal_user_id(token)
                teacher_user_id = None if admin_user_id else extract_teacher_portal_user_id(token)
                if admin_user_id:
                    user_id = admin_user_id
                    logger.info("Authenticated admin portal user: %s", _redact(user_id))
                elif teacher_user_id:
                    user_id = teacher_user_id
                    logger.info("Authenticated teacher portal user: %s", _redact(user_id))
                else:
                    is_production = settings.ENVIRONMENT == "production"
                    user_id = extract_user_id_from_token(
                        token,
                        require_verification=is_production
                    )
                    logger.info("Authenticated user: %s", _redact(user_id))
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

            # Best-effort user sync: ensure Clerk-authenticated users are present in DB
            # so admin role checks and analytics user tables can work from local data.
            # Portal (admin/teacher) users are not Clerk DB users — skip the sync.
            if user_id in (settings.ADMIN_PORTAL_USER_ID, settings.TEACHER_PORTAL_USER_ID):
                await self.app(scope, receive, send)
                return

            try:
                now = time.monotonic()
                cache_exp = _synced_user_ids.get(user_id)
                if cache_exp is None or cache_exp <= now:
                    email = extract_email_from_token(token, require_verification=is_production)
                    async with AsyncSessionLocal() as db:
                        result = await db.execute(select(User).where(User.clerk_user_id == user_id))
                        db_user = result.scalar_one_or_none()
                        if db_user is None and email:
                            result_email = await db.execute(select(User).where(User.email == email))
                            db_user = result_email.scalar_one_or_none()
                            if db_user and not db_user.clerk_user_id:
                                db_user.clerk_user_id = user_id
                                await db.commit()
                        if db_user is None and email:
                            db_user = User(
                                id=uuid.uuid4(),
                                email=email,
                                clerk_user_id=user_id,
                                role="user",
                            )
                            db.add(db_user)
                            await db.commit()
                    _synced_user_ids[user_id] = now + _SYNCED_USERS_TTL_SEC
            except Exception:
                logger.warning("Could not sync user row for %s", _redact(user_id))

            # Hand over to the next middleware/endpoint
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


