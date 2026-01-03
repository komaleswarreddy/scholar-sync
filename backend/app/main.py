"""
Main FastAPI Application Entry Point

Sets up the FastAPI app with middleware, CORS, and route registration.
Multi-tenancy is handled via middleware that extracts tenant_id from subdomain.
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import traceback

from app.core.config import settings
from app.core.middleware import tenant_middleware
from app.api.v1.endpoints import chat, sources, studio, notes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown events.
    
    Handles:
    - Database connection initialization
    - Pinecone index connection
    - Background task setup
    """
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

# CORS Middleware
# Parse CORS origins and ensure localhost:3000 is included
cors_origins_list = settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS else []
# Clean up whitespace
cors_origins_list = [origin.strip() for origin in cors_origins_list if origin.strip()]
# Ensure localhost:3000 is always included for development
if "http://localhost:3000" not in cors_origins_list:
    cors_origins_list.append("http://localhost:3000")

print(f"🔵 CORS Origins: {cors_origins_list}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Trusted Host Middleware (for production)
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*.scholarsync.com", "api.scholarsync.com"],
    )

# Tenant Middleware (must be early in the stack)
app.middleware("http")(tenant_middleware)

# API Routes
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(sources.router, prefix="/api/v1/ingest", tags=["sources"])
app.include_router(studio.router, prefix="/api/v1/studio", tags=["studio"])
app.include_router(notes.router, prefix="/api/v1/notes", tags=["notes"])


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "version": "1.0.0"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to ensure CORS headers are always set."""
    print(f"❌ Error: {type(exc).__name__}: {str(exc)}")
    print(f"❌ Traceback: {traceback.format_exc()}")
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"Internal server error: {str(exc)}",
            "type": type(exc).__name__
        },
        headers={
            "Access-Control-Allow-Origin": "http://localhost:3000",
            "Access-Control-Allow-Credentials": "true",
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
    )

