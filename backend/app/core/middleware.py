from fastapi import Request, HTTPException
from starlette.responses import JSONResponse
from sqlalchemy import select
import re
import traceback

# Import DB session and Tenant model
from app.core.database import AsyncSessionLocal
from app.models.tenant import Tenant

# Configuration for Development
DEV_TENANT_ID = "eeff7c1c-fe22-4573-ad93-a36f19ad4dc5" 
DEV_USER_ID = "dev-user-123"

EXCLUDED_PATHS = {"/", "/health", "/openapi.json", "/docs", "/api/docs", "/api/redoc"}

async def tenant_and_auth_middleware(request: Request, call_next):
    try:
        request.state.tenant_id = None
        request.state.user_id = None

        current_path = request.url.path
        is_excluded = (
            current_path == "/" or 
            any(current_path.startswith(p) for p in EXCLUDED_PATHS if p != "/")
        )

        if is_excluded:
            return await call_next(request)

        host = request.headers.get("host", "").lower()
        is_local = any(h in host for h in ["localhost", "127.0.0.1", "0.0.0.0", "testserver"])
        
        # Determine the subdomain
        subdomain = "default"
        if not is_local and host:
            subdomain_match = re.match(r"^(?P<subdomain>.+?)\.scholarsync\.com", host)
            if subdomain_match:
                subdomain = subdomain_match.group("subdomain")
            else:
                raise HTTPException(status_code=403, detail="Invalid Host Header")

        # DATABASE LOOKUP (Fulfills Phase B.a and B.b)
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Tenant).where(Tenant.subdomain == subdomain))
            tenant = result.scalar_one_or_none()

            if not tenant:
                # Task B.c: Show appropriate error messages
                return JSONResponse(
                    status_code=404, 
                    content={"detail": f"Organization '{subdomain}' not found."}
                )

            request.state.tenant_id = str(tenant.id)
            request.state.user_id = DEV_USER_ID # Placeholder for Phase C

        return await call_next(request)

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            status_code=500, 
            content={"detail": "Internal Server Error", "error": str(e)}
        )