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
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from uuid import uuid4

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
    parsed = urlparse(database_url)
    query_params = parse_qs(parsed.query)
    query_params.pop('sslmode', None)  # Remove sslmode if present
    new_query = urlencode(query_params, doseq=True)
    database_url = urlunparse(parsed._replace(query=new_query))

# Ensure the URL is properly formatted for asyncpg
# SQLAlchemy's create_async_engine should handle this, but we ensure it's correct
# For Supabase, asyncpg needs ssl=True (not a string)
connect_args = {}
engine_kwargs = {}
if "supabase.com" in database_url or "pooler.supabase.com" in database_url:
    import ssl
    # Create SSL context for Supabase connections
    # For development, we disable hostname checking (Supabase uses self-signed certs in some cases)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    connect_args = {"ssl": ssl_context}
    # Transaction pool (port 6543) + PgBouncer:
    # - asyncpg statement cache must be disabled
    # - SQLAlchemy asyncpg prepared statement cache must be disabled
    # - use NullPool because Supabase/PgBouncer already pools connections
    # - use dynamic prepared statement names to avoid clashes across pooled backends
    if ":6543" in database_url:
        connect_args["statement_cache_size"] = 0
        connect_args["prepared_statement_name_func"] = lambda: f"__asyncpg_{uuid4()}__"
        engine_kwargs["poolclass"] = NullPool
        parsed = urlparse(database_url)
        query_params = parse_qs(parsed.query)
        query_params["prepared_statement_cache_size"] = ["0"]
        new_query = urlencode(query_params, doseq=True)
        database_url = urlunparse(parsed._replace(query=new_query))

# Pool sizing: Supabase *Session* pooler (often port 5432) limits concurrent clients per
# project. Holding a connection for long SSE streams + pool_size 5+ can hit
# MaxClientsInSessionMode. Prefer Transaction pool (6543) in production; keep pool modest.
_pool_size = getattr(settings, "DB_POOL_SIZE", 5)
_max_overflow = getattr(settings, "DB_MAX_OVERFLOW", 10)
cap_enabled = bool(getattr(settings, "DB_SUPABASE_5432_POOL_CAP_ENABLED", True))
if cap_enabled and "pooler.supabase.com" in database_url and ":5432" in database_url:
    _pool_size = min(_pool_size, 3)
    _max_overflow = min(_max_overflow, 5)

_create_engine_kwargs = dict(
    echo=getattr(settings, "SQLALCHEMY_ECHO", False),
    pool_pre_ping=True,  # Verify connections before using them
    pool_recycle=3600,  # Recycle connections after 1 hour
    connect_args=connect_args,
)

if engine_kwargs.get("poolclass") is NullPool:
    _create_engine_kwargs.update(engine_kwargs)
else:
    _create_engine_kwargs.update(
        pool_size=_pool_size,
        max_overflow=_max_overflow,
        pool_timeout=30,
    )

engine = create_async_engine(database_url, **_create_engine_kwargs)

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
        yield session


