"""
Platform authentication routes — username/password login.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.middleware.auth import (
    create_platform_token,
    hash_password,
    verify_bootstrap_admin_password,
    verify_password,
)
from apps.api.middleware.login_guard import check_login_allowed, record_failure, record_success
from config.settings import settings
from packages.core.database.connection import get_db
from packages.core.database.models.user import VALID_ROLES, User

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: str
    username: Optional[str] = None
    email: Optional[str] = None
    role: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    mobile: Optional[str] = None
    institute: Optional[str] = None
    class_level: Optional[str] = None
    expertise_tier: Optional[str] = "student"
    is_active: bool = True
    is_bootstrap_admin: bool = False


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class ProfileUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    mobile: Optional[str] = None
    institute: Optional[str] = None
    class_level: Optional[str] = None


def user_to_response(user: User, *, is_bootstrap_admin: bool = False) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        role=user.role or "student",
        first_name=user.first_name,
        last_name=user.last_name,
        mobile=user.mobile,
        institute=user.institute,
        class_level=user.class_level,
        expertise_tier=getattr(user, "expertise_tier", None) or "student",
        is_active=bool(user.is_active),
        is_bootstrap_admin=is_bootstrap_admin,
    )


def bootstrap_user_response() -> UserResponse:
    return UserResponse(
        id=settings.ADMIN_PORTAL_USER_ID,
        username=settings.BOOTSTRAP_ADMIN_USERNAME,
        role="schooladmin",
        is_bootstrap_admin=True,
    )


async def _get_db_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    if user_id == settings.ADMIN_PORTAL_USER_ID:
        return None
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        return None
    result = await db.execute(select(User).where(User.id == uid))
    return result.scalar_one_or_none()


@router.post("/login", response_model=LoginResponse)
async def platform_login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Authenticate with username + password. Returns platform JWT."""
    username = (body.username or "").strip()
    password = body.password or ""
    tenant_id = getattr(request.state, "tenant_id", None)

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    check_login_allowed("platform", request, username)

    # Bootstrap admin (env credentials)
    if username == settings.BOOTSTRAP_ADMIN_USERNAME and await verify_bootstrap_admin_password(password):
        record_success("platform", request, username)
        token, expires_in = create_platform_token(settings.ADMIN_PORTAL_USER_ID, "schooladmin")
        return LoginResponse(
            access_token=token,
            expires_in=expires_in,
            user=bootstrap_user_response(),
        )

    if not tenant_id:
        record_failure("platform", request, username)
        raise HTTPException(status_code=401, detail="Invalid username or password")

    try:
        tenant_uuid = uuid.UUID(str(tenant_id))
    except ValueError:
        record_failure("platform", request, username)
        raise HTTPException(status_code=401, detail="Invalid username or password")

    result = await db.execute(
        select(User).where(
            User.tenant_id == tenant_uuid,
            User.username == username,
            User.is_active.is_(True),
        )
    )
    user = result.scalar_one_or_none()

    if not user or not user.password_hash or not await verify_password(password, user.password_hash):
        record_failure("platform", request, username)
        raise HTTPException(status_code=401, detail="Invalid username or password")

    record_success("platform", request, username)
    role = user.role if user.role in VALID_ROLES else "student"
    token, expires_in = create_platform_token(str(user.id), role)
    return LoginResponse(
        access_token=token,
        expires_in=expires_in,
        user=user_to_response(user),
    )


@router.post("/logout")
async def platform_logout():
    """Client-side token clearing; no server-side session store."""
    return {"ok": True}


@router.get("/me", response_model=UserResponse)
async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)):
    """Return the authenticated user's profile."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    if user_id == settings.ADMIN_PORTAL_USER_ID:
        return bootstrap_user_response()

    user = await _get_db_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user_to_response(user)


@router.get("/me/profile", response_model=UserResponse)
async def get_my_profile(request: Request, db: AsyncSession = Depends(get_db)):
    """Alias for profile read — same as /me."""
    return await get_current_user(request, db)


@router.patch("/me/profile", response_model=UserResponse)
async def update_my_profile(
    body: ProfileUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Update editable profile fields (not username/role)."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    if user_id == settings.ADMIN_PORTAL_USER_ID:
        raise HTTPException(status_code=400, detail="Bootstrap admin profile cannot be edited")

    user = await _get_db_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    if body.first_name is not None:
        user.first_name = body.first_name.strip() or None
    if body.last_name is not None:
        user.last_name = body.last_name.strip() or None
    if body.email is not None:
        user.email = body.email.strip().lower() or None
    if body.mobile is not None:
        user.mobile = body.mobile.strip() or None
    if body.institute is not None:
        user.institute = body.institute.strip() or None
    if body.class_level is not None:
        user.class_level = body.class_level.strip() or None

    await db.commit()
    await db.refresh(user)
    return user_to_response(user)
