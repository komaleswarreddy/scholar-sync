"""
User profile routes (alias paths for student profile UI).
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.routes.auth import (
    ProfileUpdateRequest,
    UserResponse,
    get_current_user,
    update_my_profile,
)
from packages.core.database.connection import get_db

router = APIRouter()


@router.get("/me/profile", response_model=UserResponse)
async def get_profile(request: Request, db: AsyncSession = Depends(get_db)):
    return await get_current_user(request, db)


@router.patch("/me/profile", response_model=UserResponse)
async def patch_profile(
    body: ProfileUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    return await update_my_profile(body, request, db)
