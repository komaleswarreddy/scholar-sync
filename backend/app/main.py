# app/main.py
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import traceback
from dotenv import load_dotenv

load_dotenv()

from app.core.config import settings
from app.core.middleware import tenant_and_auth_middleware
from app.api.v1.endpoints import chat, sources, studio, notes
from starlette.middleware.base import BaseHTTPMiddleware

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],  # important for Authorization header
)

# ---------------- Trusted Hosts ----------------
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*.scholarsync.com", "api.scholarsync.com"],
    )

# ---------------- Tenant + Auth Middleware ----------------
app.add_middleware(
    BaseHTTPMiddleware,
    dispatch=tenant_and_auth_middleware
)

# ---------------- Routes ----------------
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(sources.router, prefix="/api/v1/ingest", tags=["sources"])
app.include_router(studio.router, prefix="/api/v1/studio", tags=["studio"])
app.include_router(notes.router, prefix="/api/v1/notes", tags=["notes"])

# ---------------- Health ----------------
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"message": "ScholarSync API running"}

# ---------------- Global Error Handler ----------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if hasattr(exc, "status_code"):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    print(f"❌ ERROR: {exc}")
    print(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )

# ---------------- Run (for local dev) ----------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",  # Must match the module path and variable
        host="0.0.0.0",
        port=8000,
        reload=True if settings.ENVIRONMENT == "development" else False,
    )
