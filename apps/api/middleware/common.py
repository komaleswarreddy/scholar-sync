"""
Common Middleware Utilities

Shared utilities for middleware components.
"""

from starlette.responses import JSONResponse
from config.settings import settings


def add_cors_headers(response: JSONResponse, origin: str = None) -> JSONResponse:
    """Add CORS headers to a response."""
    if origin is None:
        # Default allowed origins from settings
        allowed_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
        origin = allowed_origins[0] if allowed_origins else "*"
    
    # Check if origin is allowed
    allowed_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    if origin in allowed_origins or "*" in allowed_origins or settings.ENVIRONMENT == "development":
        response.headers["Access-Control-Allow-Origin"] = origin if origin else "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Tenant-ID, x-tenant-id, Accept, Origin, X-Requested-With"
    return response


