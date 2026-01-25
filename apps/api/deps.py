"""
FastAPI Dependencies

Common dependencies for API routes.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request

from packages.core.database.connection import get_db


async def get_current_tenant_id(request: Request) -> str:
    """Get tenant ID from request state (set by middleware)."""
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise ValueError("Tenant ID not found in request state")
    return tenant_id


async def get_current_user_id(request: Request) -> str:
    """Get user ID from request state (set by middleware)."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise ValueError("User ID not found in request state")
    return user_id


# Re-export get_db for convenience
__all__ = [
    "get_db",
    "get_current_tenant_id",
    "get_current_user_id",
]


