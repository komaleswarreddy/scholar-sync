"""Unit tests for platform username/password authentication."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from apps.api.middleware.auth import (
    create_platform_token,
    extract_platform_role,
    extract_platform_user_id,
    hash_password,
    verify_bootstrap_admin_password,
    verify_password,
)
from apps.api.routes.admin_accounts import _normalize_role


def test_create_and_extract_platform_token():
    user_id = str(uuid.uuid4())
    token, expires_in = create_platform_token(user_id, "student")
    assert expires_in > 0
    assert extract_platform_user_id(token) == user_id
    assert extract_platform_role(token) == "student"


@pytest.mark.asyncio
async def test_bootstrap_admin_password_verification():
    with patch("apps.api.middleware.auth.settings") as mock_settings:
        mock_settings.BOOTSTRAP_ADMIN_PASSWORD_HASH = ""
        mock_settings.BOOTSTRAP_ADMIN_PASSWORD = "notebook123"
        assert await verify_bootstrap_admin_password("notebook123") is True
        assert await verify_bootstrap_admin_password("wrong") is False


@pytest.mark.asyncio
async def test_password_hash_roundtrip():
    hashed = await hash_password("testpassword123")
    assert await verify_password("testpassword123", hashed) is True
    assert await verify_password("wrong", hashed) is False


def test_normalize_role_valid():
    assert _normalize_role("teacher") == "teacher"
    assert _normalize_role(None) == "student"


def test_normalize_role_invalid():
    with pytest.raises(HTTPException) as exc:
        _normalize_role("superuser")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_check_admin_role_bootstrap_user():
    from apps.api.routes.admin import check_admin_role
    from config.settings import settings

    request = MagicMock()
    request.state.user_id = settings.ADMIN_PORTAL_USER_ID
    request.state.user_role = "schooladmin"
    db = AsyncMock()
    assert await check_admin_role(request, db) is True


@pytest.mark.asyncio
async def test_check_admin_role_schooladmin_jwt_claim():
    from apps.api.routes.admin import check_admin_role

    request = MagicMock()
    request.state.user_id = str(uuid.uuid4())
    request.state.user_role = "schooladmin"
    db = AsyncMock()
    assert await check_admin_role(request, db) is True


@pytest.mark.asyncio
async def test_check_admin_role_student_jwt_skips_db():
    from apps.api.routes.admin import check_admin_role

    request = MagicMock()
    request.state.user_id = str(uuid.uuid4())
    request.state.user_role = "student"
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=AssertionError("DB should not be queried"))
    assert await check_admin_role(request, db) is False
    from apps.api.routes.admin import check_admin_role

    request = MagicMock()
    uid = uuid.uuid4()
    request.state.user_id = str(uid)
    request.state.user_role = "student"

    mock_user = MagicMock()
    mock_user.role = "student"
    mock_user.is_active = True

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    assert await check_admin_role(request, db) is False
