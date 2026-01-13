"""
Main FastAPI Application Entry Point
Handles:
- Middleware
- Routes
- CORS
- Error handling
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import traceback

from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.middleware import tenant_middleware
from app.api.v1.endpoints import chat, sources, studio, notes


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown


app = FastAPI(
    title="ScholarSync API",
    description="AI Notebook Platform for Educational Institutions",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/api/redoc" if settings.ENVIRONMENT == "development" else None,
)

# ------------------- CORS -------------------
cors_origins = settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS else []
cors_origins = [o.strip() for o in cors_origins if o.strip()]
if "http://localhost:3000" not in cors_origins:
    cors_origins.append("http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------- Trusted Hosts -------------------
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*.scholarsync.com", "api.scholarsync.com"],
    )

# ------------------- Tenant + Clerk Middleware -------------------
app.add_middleware(BaseHTTPMiddleware, dispatch=tenant_middleware)

# ------------------- Routes -------------------
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(sources.router, prefix="/api/v1/ingest", tags=["sources"])
app.include_router(studio.router, prefix="/api/v1/studio", tags=["studio"])
app.include_router(notes.router, prefix="/api/v1/notes", tags=["notes"])

# ------------------- Health -------------------
@app.get("/health")
async def health():
    return {"status": "ok"}

# ------------------- Middleware Test -------------------
@app.get("/test-middleware")
async def test_middleware(request: Request):
    return {
        "tenant_id": getattr(request.state, "tenant_id", None),
        "subdomain": getattr(request.state, "subdomain", None),
        "clerk_user_id": getattr(request.state, "clerk_user_id", None),
    }

# ------------------- Global Error Handler -------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print("❌ ERROR:", exc)
    print(traceback.format_exc())

    return JSONResponse(
        status_code=500,
        content={
            "detail": f"Internal server error: {str(exc)}",
            "type": type(exc).__name__,
        },
    )

# ------------------- Run -------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
    )
