"""
Teacher Portal Auth Routes

Standalone email/password login for the teacher portal. Mirrors the admin
portal: credentials live in backend env (never in the browser bundle), the
password is compared in constant time (bcrypt hash supported), brute-force is
rate limited, and a short-lived signed HS256 JWT is returned.
"""

import hmac

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from apps.api.middleware.auth import create_teacher_portal_token, verify_portal_password
from apps.api.middleware.login_guard import (
    check_login_allowed,
    record_failure,
    record_success,
)
from config.settings import settings

router = APIRouter()


class TeacherPortalLoginRequest(BaseModel):
    email: str
    password: str


@router.post("/auth/login")
async def teacher_portal_login(body: TeacherPortalLoginRequest, request: Request):
    """Authenticate a teacher and return a signed Bearer token."""
    email = (body.email or "").strip().lower()
    password = body.password or ""
    expected_email = (settings.TEACHER_PORTAL_EMAIL or "").strip().lower()

    check_login_allowed("teacher", request, email)

    email_ok = hmac.compare_digest(email.encode("utf-8"), expected_email.encode("utf-8"))
    password_ok = await verify_portal_password(
        password, settings.TEACHER_PORTAL_PASSWORD, settings.TEACHER_PORTAL_PASSWORD_HASH
    )
    if not (email_ok and password_ok):
        record_failure("teacher", request, email)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    record_success("teacher", request, email)
    access_token, expires_in = create_teacher_portal_token()
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": expires_in,
    }
