# apps/api/main.py
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import traceback
from dotenv import load_dotenv

load_dotenv()
 
from config.settings import settings
from apps.api.middleware.tenant import TenantMiddleware
from apps.api.routes import chat, sources, studio, notes, health

# ---------------- Lifespan ----------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic here if needed
    yield
    # Shutdown logic here if needed

# ---------------- App ----------------
app = FastAPI(
    title="ScholarSync API",
    description="AI Notebook Platform for Educational Institutions",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/api/redoc" if settings.ENVIRONMENT == "development" else None,
    redirect_slashes=True,
)

# ---------------- CORS ----------------
# Parse CORS origins from environment variable
cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]

# Production: Validate that CORS origins are configured (not wildcard)
if settings.ENVIRONMENT == "production" and not cors_origins:
    raise ValueError("CORS_ORIGINS must be set in production environment")

# Production: Ensure no wildcard origins
if settings.ENVIRONMENT == "production" and "*" in cors_origins:
    raise ValueError("Wildcard CORS origins (*) are not allowed in production")

# Define allowed headers - more restrictive in production
if settings.ENVIRONMENT == "production":
    allowed_headers = [
        "Authorization",
        "Content-Type",
        "X-Tenant-ID",
        "x-tenant-id",
        "Accept",
        "Origin",
        "X-Requested-With",
    ]
else:
    # Development: Allow all headers for easier testing
    allowed_headers = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=allowed_headers,
    expose_headers=["Content-Type", "Authorization"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

# ---------------- Trusted Hosts ----------------
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*.scholarsync.com", "api.scholarsync.com"],
    )

# ---------------- Tenant + Auth Middleware ----------------
app.add_middleware(TenantMiddleware)

# ---------------- Routes ----------------
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(sources.router, prefix="/api/v1/ingest", tags=["sources"])
app.include_router(studio.router, prefix="/api/v1/studio", tags=["studio"])
app.include_router(notes.router, prefix="/api/v1/notes", tags=["notes"])
app.include_router(health.router, tags=["health"])

# ---------------- Health ----------------
@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"message": "ScholarSync API running"}

# ---------------- Favicon ----------------
@app.get("/favicon.ico")
async def favicon():
    """Handle favicon requests - return 204 No Content (standard for missing favicon)"""
    from fastapi.responses import Response
    return Response(status_code=204)

# ---------------- Debug: Show Current User (Development Only) ----------------
@app.get("/api/v1/debug/user")
async def debug_user(request: Request):
    """
    Debug endpoint to show current authenticated user.
    Only available in development mode.
    """
    if settings.ENVIRONMENT != "development":
        raise HTTPException(status_code=404, detail="Not found")
    
    user_id = getattr(request.state, "user_id", None)
    tenant_id = getattr(request.state, "tenant_id", None)
    auth_header = request.headers.get("Authorization", "")
    has_token = bool(auth_header and auth_header.startswith("Bearer "))
    
    return {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "has_authorization_header": has_token,
        "authorization_header_present": bool(auth_header),
        "environment": settings.ENVIRONMENT,
        "message": "This endpoint shows authentication status (dev mode only)"
    }

# ---------------- Global Error Handler ----------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if hasattr(exc, "status_code"):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    print(f"[ERROR] ERROR: {exc}")
    print(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )

# ---------------- Run (for local dev) ----------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "apps.api.main:app",  # Updated module path
        host="0.0.0.0",
        port=8000,
        reload=True if settings.ENVIRONMENT == "development" else False,
    )


