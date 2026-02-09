"""
Tenant Middleware

Handles tenant extraction from subdomain and authentication.
Sets tenant_id and user_id in request state.
"""

from fastapi import Request, HTTPException
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Scope, Receive, Send
from sqlalchemy import select
import re
import traceback

from packages.core.database.connection import AsyncSessionLocal
from packages.core.database.models.tenant import Tenant
from apps.api.middleware.auth import extract_user_id_from_token
from apps.api.middleware.common import add_cors_headers
from config.settings import settings

# Configuration for Development
DEV_TENANT_ID = "eeff7c1c-fe22-4573-ad93-a36f19ad4dc5"
EXCLUDED_PATHS = {"/", "/health", "/openapi.json", "/docs", "/api/docs", "/api/redoc", "/favicon.ico", "/.well-known", "/metrics"}

# Paths that require tenant but not user authentication (development only)
# These paths can work with just tenant_id from subdomain, no JWT required
TENANT_ONLY_PATHS = {"/api/v1/metrics", "/api/v1/dashboards", "/api/v1/alerts", "/debug"}


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

            # Step 3: Database lookup for tenant
            tenant_id = None
            try:
                async with AsyncSessionLocal() as db:
                    result = await db.execute(select(Tenant).where(Tenant.subdomain == subdomain))
                    tenant = result.scalar_one_or_none()

                    if tenant:
                        tenant_id = str(tenant.id)
                        print(f"[SUCCESS] Tenant found: {subdomain} -> {tenant_id}")
                    else:
                        if settings.ENVIRONMENT == "development":
                            print(f"[WARNING] Tenant '{subdomain}' not found in DB, using fallback: {DEV_TENANT_ID}")
                            tenant_id = DEV_TENANT_ID
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

            # Check if this is a tenant-only path (metrics/dashboards in development)
            is_tenant_only_path = (
                settings.ENVIRONMENT == "development" and
                any(current_path.startswith(path) for path in TENANT_ONLY_PATHS)
            )
            
            # Step 4: Extract user_id from Authorization header
            auth_header = request.headers.get("Authorization", "")
            user_id = None
            
            # For tenant-only paths in development, skip user authentication
            if is_tenant_only_path:
                print(f"[INFO] [MIDDLEWARE] Tenant-only path '{current_path}' - skipping user authentication in development mode")
                request.state.user_id = None  # No user required
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
                is_production = settings.ENVIRONMENT == "production"
                user_id = extract_user_id_from_token(
                    token, 
                    require_verification=is_production
                )
                print(f"[SUCCESS] Authenticated user: {user_id}")
            except HTTPException as e:
                print(f"[WARNING] Token verification failed: {e.detail}")
                resp = JSONResponse(
                    status_code=401,
                    content={
                        "detail": f"Invalid or expired authentication token: {e.detail}",
                        "error_code": "INVALID_TOKEN"
                    }
                )
                resp = add_cors_headers(resp, origin)
                await resp(scope, receive, send)
                return
            except Exception as e:
                print(f"[WARNING] Error extracting user from token: {str(e)}")
                traceback.print_exc()
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

            # Hand over to the next middleware/endpoint
            await self.app(scope, receive, send)

        except Exception as e:
            traceback.print_exc()
            origin = request.headers.get("Origin", "") if 'request' in locals() else None
            resp = JSONResponse(
                status_code=500, 
                content={"detail": "Internal Server Error", "error": str(e)}
            )
            resp = add_cors_headers(resp, origin)
            await resp(scope, receive, send)


