"""
Lightweight in-process brute-force guard for portal logins.

Tracks failed attempts per (scope, ip, email) inside a sliding window and
applies a temporary lockout once the threshold is exceeded.

NOTE: This is in-memory and therefore per-process. It is sufficient for the
single-instance MVP. For a multi-instance deployment, back this with Redis
(see docs/PRODUCTION_DEPLOYMENT_GUIDE.md section 7.2).
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from fastapi import HTTPException, Request

from config.settings import settings


@dataclass
class _Attempts:
    times: list[float] = field(default_factory=list)
    locked_until: float = 0.0


_lock = threading.Lock()
_store: dict[str, _Attempts] = {}


def _client_ip(request: Request) -> str:
    # Honor a single reverse proxy hop if present; fall back to socket peer.
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _key(scope: str, request: Request, email: str) -> str:
    return f"{scope}:{_client_ip(request)}:{(email or '').strip().lower()}"


def check_login_allowed(scope: str, request: Request, email: str) -> None:
    """Raise HTTP 429 if this caller is currently locked out."""
    now = time.monotonic()
    key = _key(scope, request, email)
    with _lock:
        rec = _store.get(key)
        if rec and rec.locked_until > now:
            retry_after = int(rec.locked_until - now) + 1
            raise HTTPException(
                status_code=429,
                detail="Too many failed login attempts. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )


def record_failure(scope: str, request: Request, email: str) -> None:
    """Record a failed attempt and lock the caller out once the threshold is hit."""
    now = time.monotonic()
    window = settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS
    max_attempts = settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS
    key = _key(scope, request, email)
    with _lock:
        rec = _store.get(key) or _Attempts()
        rec.times = [t for t in rec.times if now - t < window]
        rec.times.append(now)
        if len(rec.times) >= max_attempts:
            rec.locked_until = now + settings.LOGIN_RATE_LIMIT_LOCKOUT_SECONDS
            rec.times = []
        _store[key] = rec


def record_success(scope: str, request: Request, email: str) -> None:
    """Clear the failure history after a successful login."""
    with _lock:
        _store.pop(_key(scope, request, email), None)
