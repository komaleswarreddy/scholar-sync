"""
Admin account management — create/list/update platform users.
"""

from __future__ import annotations

import uuid
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.middleware.auth import hash_password
from apps.api.routes.admin import check_admin_role, invalidate_users_list_cache
from apps.api.routes.auth import UserResponse, user_to_response
from packages.core.database.connection import get_db
from packages.core.database.models.user import VALID_ROLES, User
from packages.core.iil.enums import ExpertiseTier, default_expertise_tier_for_role

router = APIRouter()


class CreateAccountRequest(BaseModel):
    username: str
    password: str = Field(min_length=8)
    role: Optional[str] = "student"
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    mobile: Optional[str] = None
    institute: Optional[str] = None
    class_level: Optional[str] = None
    expertise_tier: Optional[str] = None


class UpdateAccountRequest(BaseModel):
    role: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=8)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    mobile: Optional[str] = None
    institute: Optional[str] = None
    class_level: Optional[str] = None
    expertise_tier: Optional[str] = None
    is_active: Optional[bool] = None


class AccountListResponse(BaseModel):
    items: List[UserResponse]
    total: int


def _normalize_role(role: Optional[str]) -> str:
    r = (role or "student").strip().lower()
    if r not in VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {', '.join(sorted(VALID_ROLES))}",
        )
    return r


def _normalize_expertise_tier(tier: Optional[str], role: str) -> str:
    t = (tier or "").strip().lower()
    valid = {e.value for e in ExpertiseTier}
    if t in valid:
        return t
    return default_expertise_tier_for_role(role)


async def _require_schooladmin(request: Request, db: AsyncSession) -> None:
    is_admin = await check_admin_role(request, db, raise_on_db_unavailable=True)
    if not is_admin:
        raise HTTPException(status_code=403, detail="School admin access required")


@router.post("/accounts", response_model=UserResponse, status_code=201)
async def create_account(
    body: CreateAccountRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await _require_schooladmin(request, db)

    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")

    username = (body.username or "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")

    try:
        tenant_uuid = uuid.UUID(str(tenant_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant")

    existing = await db.execute(
        select(User).where(User.tenant_id == tenant_uuid, User.username == username)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already exists for this organization")

    role = _normalize_role(body.role)
    expertise_tier = _normalize_expertise_tier(body.expertise_tier, role)
    user = User(
        tenant_id=tenant_uuid,
        username=username,
        password_hash=await hash_password(body.password),
        role=role,
        expertise_tier=expertise_tier,
        first_name=(body.first_name or "").strip() or None,
        last_name=(body.last_name or "").strip() or None,
        email=(body.email or "").strip().lower() or None,
        mobile=(body.mobile or "").strip() or None,
        institute=(body.institute or "").strip() or None,
        class_level=(body.class_level or "").strip() or None,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    invalidate_users_list_cache(str(tenant_id))
    return user_to_response(user)


@router.get("/accounts", response_model=AccountListResponse)
async def list_accounts(
    request: Request,
    db: AsyncSession = Depends(get_db),
    role: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    await _require_schooladmin(request, db)

    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")

    try:
        tenant_uuid = uuid.UUID(str(tenant_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant")

    query = select(User).where(User.tenant_id == tenant_uuid)
    if role:
        query = query.where(User.role == role.strip().lower())
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            (User.username.ilike(term))
            | (User.email.ilike(term))
            | (User.first_name.ilike(term))
            | (User.last_name.ilike(term))
        )

    result = await db.execute(query.order_by(User.created_at.desc()).limit(limit).offset(offset))
    users = result.scalars().all()
    return AccountListResponse(
        items=[user_to_response(u) for u in users],
        total=len(users),
    )


@router.patch("/accounts/{account_id}", response_model=UserResponse)
async def update_account(
    account_id: str,
    body: UpdateAccountRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await _require_schooladmin(request, db)

    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")

    try:
        tenant_uuid = uuid.UUID(str(tenant_id))
        user_uuid = uuid.UUID(account_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid id")

    result = await db.execute(
        select(User).where(User.id == user_uuid, User.tenant_id == tenant_uuid)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Account not found")

    if body.role is not None:
        user.role = _normalize_role(body.role)
    if body.password:
        user.password_hash = await hash_password(body.password)
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
    if body.expertise_tier is not None:
        user.expertise_tier = _normalize_expertise_tier(body.expertise_tier, user.role)
    if body.is_active is not None:
        user.is_active = body.is_active

    await db.commit()
    await db.refresh(user)
    invalidate_users_list_cache(str(tenant_id))
    return user_to_response(user)


@router.delete("/accounts/{account_id}", status_code=204)
async def delete_account(
    account_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Permanently remove a platform user account."""
    await _require_schooladmin(request, db)

    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")

    try:
        tenant_uuid = uuid.UUID(str(tenant_id))
        user_uuid = uuid.UUID(account_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid id")

    result = await db.execute(
        select(User).where(User.id == user_uuid, User.tenant_id == tenant_uuid)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Account not found")

    await db.delete(user)
    await db.commit()
    invalidate_users_list_cache(str(tenant_id))
