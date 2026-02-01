"""
CORS Wrapper Middleware

Ensures CORS headers are always added to responses, even for errors.
This works as a backup to FastAPI's CORSMiddleware.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from config.settings import settings
import traceback


class CORSWrapperMiddleware(BaseHTTPMiddleware):
    """
    Wrapper middleware that ensures CORS headers are always present.
    This runs after CORSMiddleware to catch any responses that might have missed CORS headers.
    """
    
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("Origin", "")
        
        # Get allowed origins
        allowed_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
        
        # Check if origin is allowed
        is_allowed = (
            origin in allowed_origins or 
            "*" in allowed_origins or 
            settings.ENVIRONMENT == "development" or
            not origin  # Allow if no origin (same-origin request)
        )
        
        # Determine which origin to use
        cors_origin = origin if origin and is_allowed else (allowed_origins[0] if allowed_origins else "*")
        
        try:
            response = await call_next(request)
        except Exception as e:
            # If an exception occurs, create a response with CORS headers
            from starlette.responses import JSONResponse
            
            print(f"[CORS WRAPPER] Exception caught: {type(e).__name__}: {e}")
            print(traceback.format_exc())
            
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "type": type(e).__name__, "message": str(e)}
            )
        
        # Always add CORS headers if not already present
        # In development, always add headers regardless of origin check
        should_add_headers = (
            "Access-Control-Allow-Origin" not in response.headers and
            (is_allowed or settings.ENVIRONMENT == "development")
        )
        
        if should_add_headers:
            # For StreamingResponse, we need to add headers to the initial response
            if isinstance(response, StreamingResponse):
                response.headers["Access-Control-Allow-Origin"] = cors_origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
                response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Tenant-ID, x-tenant-id, Accept, Origin, X-Requested-With"
            else:
                # For regular responses, add headers normally
                response.headers["Access-Control-Allow-Origin"] = cors_origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
                response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Tenant-ID, x-tenant-id, Accept, Origin, X-Requested-With"
        
        return response
