from fastapi import Request, HTTPException
from starlette.responses import JSONResponse
from sqlalchemy import select
import re
import traceback

# Import DB session and Tenant model
from app.core.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.core.auth import extract_user_id_from_token
from app.core.config import settings

# Configuration for Development
DEV_TENANT_ID = "eeff7c1c-fe22-4573-ad93-a36f19ad4dc5"

EXCLUDED_PATHS = {"/", "/health", "/openapi.json", "/docs", "/api/docs", "/api/redoc"}

async def tenant_and_auth_middleware(request: Request, call_next):
    """
    End-to-End Middleware Flow:
    1. Check if path is excluded (health, docs, etc.) → Skip middleware
    2. Extract subdomain from host header
    3. Connect to database and lookup tenant by subdomain
    4. Extract user_id from Authorization header (JWT token)
    5. Set tenant_id and user_id in request.state
    6. Continue to next middleware/endpoint
    """
    try:
        # Initialize request state
        request.state.tenant_id = None
        request.state.user_id = None

        # Step 1: Check if path is excluded OR if it's a CORS preflight request
        current_path = request.url.path
        is_excluded = (
            current_path == "/" or 
            any(current_path.startswith(p) for p in EXCLUDED_PATHS if p != "/")
        )
        
        # Skip middleware for OPTIONS requests (CORS preflight)
        # SECURITY NOTE: This is safe and standard practice because:
        # 1. OPTIONS requests are browser-initiated preflight checks
        # 2. They don't contain actual data or authentication tokens
        # 3. CORS middleware (which runs BEFORE this) validates the origin
        # 4. The actual request (GET/POST/etc) will still go through full auth middleware
        # 5. This is the recommended approach per FastAPI and CORS standards
        if request.method == "OPTIONS":
            return await call_next(request)

        if is_excluded:
            return await call_next(request)

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
                    print(f"✅ Tenant found: {subdomain} → {tenant_id}")
                else:
                    # Tenant not found in database
                    if settings.ENVIRONMENT == "development":
                        # In dev mode, use fallback tenant if not found
                        print(f"⚠️ Tenant '{subdomain}' not found in DB, using fallback: {DEV_TENANT_ID}")
                        tenant_id = DEV_TENANT_ID
                    else:
                        # In production, return 404 if tenant doesn't exist
                        return JSONResponse(
                            status_code=404, 
                            content={"detail": f"Organization '{subdomain}' not found."}
                        )
        except Exception as db_error:
            # Database connection error
            error_msg = str(db_error)
            print(f"❌ Database connection error: {error_msg}")
            
            if settings.ENVIRONMENT == "development":
                # In dev mode, use fallback tenant if database is unavailable
                print(f"⚠️ Database unavailable, using fallback tenant: {DEV_TENANT_ID}")
                tenant_id = DEV_TENANT_ID
            else:
                # In production, fail if database is unavailable
                return JSONResponse(
                    status_code=503,
                    content={"detail": "Database unavailable. Please try again later."}
                )

        # Set tenant_id in request state
        request.state.tenant_id = tenant_id

        # Step 4: Extract user_id from Authorization header (JWT token)
        auth_header = request.headers.get("Authorization", "")
        user_id = None
        
        if not auth_header or not auth_header.startswith("Bearer "):
            # No token provided
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Authentication required. Please provide a valid Bearer token in the Authorization header.",
                    "error_code": "MISSING_TOKEN"
                }
            )
        
        token = auth_header.replace("Bearer ", "").strip()
        if not token:
            # Empty token
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Invalid authentication token. Token cannot be empty.",
                    "error_code": "EMPTY_TOKEN"
                }
            )
        
        try:
            # Extract user_id from token
            # In dev mode, decode without full verification for easier testing
            # In production, require full verification
            is_production = settings.ENVIRONMENT == "production"
            user_id = extract_user_id_from_token(
                token, 
                require_verification=is_production
            )
            print(f"✅ Authenticated user: {user_id}")
        except HTTPException as e:
            # Token verification failed - return proper error
            print(f"⚠️ Token verification failed: {e.detail}")
            return JSONResponse(
                status_code=401,
                content={
                    "detail": f"Invalid or expired authentication token: {e.detail}",
                    "error_code": "INVALID_TOKEN"
                }
            )
        except Exception as e:
            # Unexpected error during token extraction
            print(f"⚠️ Error extracting user from token: {str(e)}")
            traceback.print_exc()
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Authentication error. Could not validate credentials.",
                    "error_code": "AUTH_ERROR"
                }
            )
        
        # Step 5: Set user_id (must be extracted from token)
        if not user_id:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Authentication failed. User ID could not be extracted from token.",
                    "error_code": "MISSING_USER_ID"
                }
            )
        
        request.state.user_id = user_id

        # Step 6: Continue to next middleware/endpoint
        return await call_next(request)

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            status_code=500, 
            content={"detail": "Internal Server Error", "error": str(e)}
        )