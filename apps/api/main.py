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
from apps.api.routes import chat, sources, studio, notes, health, metrics, alerts, dashboards, debug

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
app.include_router(metrics.router, prefix="/api/v1/metrics", tags=["metrics"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])
app.include_router(dashboards.router, prefix="/api/v1/dashboards", tags=["dashboards"])
app.include_router(debug.router, prefix="/debug", tags=["debug"])
app.include_router(health.router, tags=["health"])

# ---------------- Health ----------------
@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"message": "ScholarSync API running"}


# ---------------- Metrics (Prometheus-style) ----------------
@app.get("/metrics")
async def prometheus_metrics(request: Request):
    """
    Prometheus-style metrics endpoint.
    
    Returns metrics in Prometheus text format for scraping.
    """
    from fastapi.responses import Response
    from packages.core.monitoring.metrics import get_metrics_collector
    
    tenant_id = getattr(request.state, "tenant_id", None)
    metrics = get_metrics_collector()
    
    # Get metrics summary
    summary = metrics.get_metrics_summary(tenant_id=tenant_id)
    
    # Format as Prometheus metrics
    lines = []
    
    # LLM calls
    llm_calls = summary.get("llm_calls", {})
    lines.append(f"# HELP scholarsync_llm_calls_total Total number of LLM API calls")
    lines.append(f"# TYPE scholarsync_llm_calls_total counter")
    lines.append(f'scholarsync_llm_calls_total{{tenant_id="{tenant_id or "unknown"}"}} {llm_calls.get("total", 0)}')
    
    # Tokens
    tokens = summary.get("tokens", {})
    lines.append(f"# HELP scholarsync_tokens_total Total tokens consumed")
    lines.append(f"# TYPE scholarsync_tokens_total counter")
    lines.append(f'scholarsync_tokens_input_total{{tenant_id="{tenant_id or "unknown"}"}} {tokens.get("input", 0)}')
    lines.append(f'scholarsync_tokens_output_total{{tenant_id="{tenant_id or "unknown"}"}} {tokens.get("output", 0)}')
    lines.append(f'scholarsync_tokens_total{{tenant_id="{tenant_id or "unknown"}"}} {tokens.get("total", 0)}')
    
    # Costs
    costs = summary.get("costs", {})
    lines.append(f"# HELP scholarsync_costs_total Total cost in USD")
    lines.append(f"# TYPE scholarsync_costs_total counter")
    lines.append(f'scholarsync_costs_total{{tenant_id="{tenant_id or "unknown"}"}} {costs.get("total", 0.0)}')
    
    # Cache
    cache = summary.get("cache", {})
    lines.append(f"# HELP scholarsync_cache_operations_total Total cache operations")
    lines.append(f"# TYPE scholarsync_cache_operations_total counter")
    lines.append(f'scholarsync_cache_hits_total{{tenant_id="{tenant_id or "unknown"}"}} {cache.get("hits", 0)}')
    lines.append(f'scholarsync_cache_misses_total{{tenant_id="{tenant_id or "unknown"}"}} {cache.get("misses", 0)}')
    
    # Cache hit rate
    hit_rate = metrics.get_cache_hit_rate(tenant_id=tenant_id)
    lines.append(f"# HELP scholarsync_cache_hit_rate Cache hit rate (0-1)")
    lines.append(f"# TYPE scholarsync_cache_hit_rate gauge")
    lines.append(f'scholarsync_cache_hit_rate{{tenant_id="{tenant_id or "unknown"}"}} {hit_rate}')
    
    # Feature usage
    features = summary.get("features", {})
    lines.append(f"# HELP scholarsync_feature_usage_total Feature usage count")
    lines.append(f"# TYPE scholarsync_feature_usage_total counter")
    for feature, count in features.items():
        lines.append(f'scholarsync_feature_usage_total{{tenant_id="{tenant_id or "unknown"}",feature="{feature}"}} {count}')
    
    # Return as text/plain for Prometheus
    return Response(
        content="\n".join(lines) + "\n",
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )

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


