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

from app.core.config import settings

# ======================
# Database Engine
# ======================
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,  # logs SQL queries (safe for dev)
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
