# apps/api/main.py
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import traceback
from dotenv import load_dotenv
import sys
import logging

# ========== CONFIGURE LOGGING FOR IMMEDIATE DISPLAY ==========
# Ensure all logs are immediately flushed and visible in terminal
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    stream=sys.stdout,
    force=True
)
# DISABLE VERBOSE HTTPX DEBUG LOGGING (HTTP/2 frame encoding/decoding noise)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('h2').setLevel(logging.WARNING)
logging.getLogger('hpack').setLevel(logging.WARNING)

# Also flush print statements immediately
sys.stdout.flush()
sys.stderr.flush()
# ========== END LOGGING CONFIG ==========

# Custom print function with immediate flush
def log_msg(msg):
    """Print immediately with flush"""
    print(msg, flush=True)
    sys.stdout.flush()

# Export for use in other modules
import builtins
_original_print = builtins.print
def flushed_print(*args, **kwargs):
    """Override print to always flush"""
    kwargs['flush'] = True
    return _original_print(*args, **kwargs)
builtins.print = flushed_print

load_dotenv()

# ========== MONKEY PATCH: Fix httpx.AsyncClient proxies incompatibility ==========
# Supabase 2.28.2 tries to pass 'proxies' parameter to httpx.AsyncClient,
# but httpx 0.25.2 doesn't accept it. This patch removes the proxies argument
# before AsyncClient initialization.
import httpx
_original_async_client_init = httpx.AsyncClient.__init__

def patched_async_client_init(self, *args, **kwargs):
    # Remove 'proxies' from kwargs if present (supabase passes this but httpx 0.25.2 doesn't support it)
    kwargs.pop('proxies', None)
    return _original_async_client_init(self, *args, **kwargs)

httpx.AsyncClient.__init__ = patched_async_client_init
# ========== END MONKEY PATCH ==========
 
from config.settings import settings
from apps.api.middleware.tenant import TenantMiddleware
from apps.api.routes import chat, sources, studio, notes, health, metrics, dashboards, alerts, admin, admin_ncert_global, pipeline_traces

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

# ---------------- Trusted Hosts ----------------
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*.scholarsync.com", "api.scholarsync.com"],
    )

# ---------------- Tenant + Auth Middleware ----------------
app.add_middleware(TenantMiddleware)

# ---------------- CORS ----------------
# NOTE: CORS must be the OUTERMOST middleware so preflight (OPTIONS) and error
# responses always include Access-Control-* headers.
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

# ---------------- Routes ----------------
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(sources.router, prefix="/api/v1/ingest", tags=["sources"])
app.include_router(studio.router, prefix="/api/v1/studio", tags=["studio"])
app.include_router(notes.router, prefix="/api/v1/notes", tags=["notes"])
app.include_router(health.router, tags=["health"])
app.include_router(metrics.router, prefix="/api/v1/metrics", tags=["metrics"])
app.include_router(dashboards.router, prefix="/api/v1/dashboards", tags=["dashboards"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(admin_ncert_global.router, prefix="/api/v1/admin", tags=["admin-ncert-global"])
app.include_router(pipeline_traces.router, prefix="/api/v1/pipeline-traces", tags=["pipeline-traces"])

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


