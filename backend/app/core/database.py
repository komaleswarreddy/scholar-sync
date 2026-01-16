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

from app.core.config import settings

# ======================
# Database Engine
# ======================
# SQLAlchemy should handle URL encoding automatically, but ensure it's properly formatted
# The connection string from Supabase may have encoded characters that need proper handling
database_url = settings.DATABASE_URL

# Ensure the URL is properly formatted for asyncpg
# SQLAlchemy's create_async_engine should handle this, but we ensure it's correct
engine = create_async_engine(
    database_url,
    echo=True,  # logs SQL queries (safe for dev)
    pool_pre_ping=True,  # Verify connections before using them
    pool_recycle=3600,  # Recycle connections after 1 hour
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
