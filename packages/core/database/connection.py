"""
Database Configuration and Session Management

PostgreSQL + SQLAlchemy (Async)
Simple, stable, and beginner-safe setup.
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator
from urllib.parse import quote_plus, unquote

from config.settings import settings

# ======================
# Database Engine
# ======================
# SQLAlchemy should handle URL encoding automatically, but ensure it's properly formatted
# The connection string from Supabase may have encoded characters that need proper handling
database_url = settings.DATABASE_URL

# Auto-convert postgresql:// to postgresql+asyncpg:// for async SQLAlchemy
if database_url.startswith("postgresql://") and not database_url.startswith("postgresql+asyncpg://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    print(f"[DATABASE] Auto-converted connection string to async format")

# Remove sslmode from URL if present (asyncpg doesn't use URL parameters for SSL)
# We'll handle SSL via connect_args instead
if "sslmode" in database_url:
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    parsed = urlparse(database_url)
    query_params = parse_qs(parsed.query)
    query_params.pop('sslmode', None)  # Remove sslmode if present
    new_query = urlencode(query_params, doseq=True)
    database_url = urlunparse(parsed._replace(query=new_query))

# Ensure the URL is properly formatted for asyncpg
# SQLAlchemy's create_async_engine should handle this, but we ensure it's correct
# For Supabase, asyncpg needs ssl=True (not a string)
connect_args = {}
if "supabase.com" in database_url or "pooler.supabase.com" in database_url:
    import ssl
    # Create SSL context for Supabase connections
    # For development, we disable hostname checking (Supabase uses self-signed certs in some cases)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    connect_args = {"ssl": ssl_context}

engine = create_async_engine(
    database_url,
    echo=getattr(settings, "SQLALCHEMY_ECHO", False),
    pool_pre_ping=True,  # Verify connections before using them
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_size=getattr(settings, "DB_POOL_SIZE", 5),
    max_overflow=getattr(settings, "DB_MAX_OVERFLOW", 10),
    connect_args=connect_args,
)

# ======================
# Session Factory
# ======================
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ======================
# Base Model
# ======================
Base = declarative_base()

# ======================
# Dependency
# ======================
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


