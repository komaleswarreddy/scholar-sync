"""
Authentication Middleware

Handles JWT token extraction and verification for Clerk (student) auth and the
standalone admin/teacher portal tokens.

Security model
--------------
- Clerk student tokens are RS256 and are verified against Clerk's public key
  (`CLERK_JWT_PUBLIC_KEY`) or, preferably, Clerk's JWKS endpoint (`CLERK_JWKS_URL`).
- Verification is FAIL-CLOSED: if verification material is configured, the
  signature/expiry/issuer/audience are always checked. The old "decode without
  verification" path is only ever reachable in local development when NO
  verification material is configured, and it logs a loud warning.
- Admin/teacher portal tokens are short-lived HS256 JWTs signed with per-portal
  secrets. Passwords are compared in constant time and may be stored as bcrypt
  hashes.
"""

from datetime import datetime, timedelta, timezone
import hmac
import json
import logging
import time
import urllib.request
from typing import Optional

import bcrypt
from jose import jwt, JWTError
from fastapi import HTTPException

from config.settings import settings

logger = logging.getLogger("scholarsync.auth")

# bcrypt only uses the first 72 bytes of a password; truncate explicitly so long
# inputs never raise on newer bcrypt releases.
_BCRYPT_MAX_BYTES = 72

# JWKS cache (Clerk rotates keys rarely; cache to avoid a network call per request)
_JWKS_TTL_SECONDS = 3600.0
_jwks_cache: dict[str, object] = {"keys": None, "exp": 0.0}


# --------------------------------------------------------------------------- #
# Password helpers
# --------------------------------------------------------------------------- #
def hash_password(plain: str) -> str:
    """Return a bcrypt hash for a plaintext password (use to generate *_HASH env vars)."""
    pw = (plain or "").encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time bcrypt verification (bcrypt.checkpw). Returns False on any error."""
    try:
        pw = (plain or "").encode("utf-8")[:_BCRYPT_MAX_BYTES]
        return bcrypt.checkpw(pw, (hashed or "").encode("utf-8"))
    except Exception:
        return False


def verify_portal_password(plain: str, configured_password: str, configured_hash: str) -> bool:
    """
    Verify a portal password against either a bcrypt hash (preferred) or a
    plaintext value (dev fallback). Both paths are constant-time to avoid
    timing oracles.
    """
    if configured_hash:
        return verify_password(plain, configured_hash)
    return hmac.compare_digest((plain or "").encode("utf-8"), (configured_password or "").encode("utf-8"))


# --------------------------------------------------------------------------- #
# Admin / teacher portal tokens (HS256)
# --------------------------------------------------------------------------- #
def _create_portal_token(user_id: str, secret: str, ttl_hours: int, claim: str) -> tuple[str, int]:
    ttl_hours = max(1, int(ttl_hours))
    expires_in = ttl_hours * 3600
    exp = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    payload = {"sub": user_id, claim: True, "exp": exp}
    token = jwt.encode(payload, secret, algorithm="HS256")
    return token, expires_in


def _extract_portal_user_id(token: str, secret: str, claim: str) -> Optional[str]:
    if not token or not secret:
        return None
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        if payload.get(claim) and payload.get("sub"):
            return str(payload["sub"])
    except JWTError:
        return None
    return None


def create_admin_portal_token() -> tuple[str, int]:
    """Issue HS256 JWT for standalone admin portal login."""
    return _create_portal_token(
        settings.ADMIN_PORTAL_USER_ID,
        settings.ADMIN_PORTAL_JWT_SECRET,
        settings.ADMIN_PORTAL_TOKEN_TTL_HOURS,
        "admin_portal",
    )


def extract_admin_portal_user_id(token: str) -> Optional[str]:
    """Return admin portal user id when token is a valid admin portal JWT."""
    return _extract_portal_user_id(token, settings.ADMIN_PORTAL_JWT_SECRET, "admin_portal")


def create_teacher_portal_token() -> tuple[str, int]:
    """Issue HS256 JWT for standalone teacher portal login."""
    return _create_portal_token(
        settings.TEACHER_PORTAL_USER_ID,
        settings.TEACHER_PORTAL_JWT_SECRET,
        settings.TEACHER_PORTAL_TOKEN_TTL_HOURS,
        "teacher_portal",
    )


def extract_teacher_portal_user_id(token: str) -> Optional[str]:
    """Return teacher portal user id when token is a valid teacher portal JWT."""
    return _extract_portal_user_id(token, settings.TEACHER_PORTAL_JWT_SECRET, "teacher_portal")


# --------------------------------------------------------------------------- #
# Clerk JWT verification (RS256)
# --------------------------------------------------------------------------- #
def _get_clerk_jwks() -> Optional[list]:
    """Fetch and cache Clerk's JWKS key set. Returns None when no JWKS URL configured."""
    url = settings.CLERK_JWKS_URL
    if not url:
        return None
    now = time.monotonic()
    cached = _jwks_cache.get("keys")
    if cached and float(_jwks_cache.get("exp", 0)) > now:
        return cached  # type: ignore[return-value]
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:  # nosec B310 - fixed https config URL
            data = json.loads(resp.read().decode("utf-8"))
        keys = data.get("keys", [])
        _jwks_cache["keys"] = keys
        _jwks_cache["exp"] = now + _JWKS_TTL_SECONDS
        return keys
    except Exception as exc:
        logger.warning("Failed to fetch Clerk JWKS: %s", type(exc).__name__)
        return cached if cached else None  # type: ignore[return-value]


def _decode_clerk_token(token: str, require_verification: bool) -> dict:
    """
    Decode a Clerk JWT.

    Verification is mandatory whenever verification material is configured.
    The unverified path is only reachable in local development when neither a
    public key nor a JWKS URL is configured.
    """
    audience = settings.CLERK_JWT_AUDIENCE or None
    issuer = settings.CLERK_ISSUER or None

    # 1) Preferred: JWKS verification (handles Clerk key rotation)
    if settings.CLERK_JWKS_URL:
        keys = _get_clerk_jwks()
        if keys:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            key = next((k for k in keys if k.get("kid") == kid), None)
            if key is None:
                raise HTTPException(status_code=401, detail="Invalid authentication token")
            return jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=audience,
                issuer=issuer,
                options={"verify_signature": True, "verify_exp": True},
            )

    # 2) Static PEM public key verification
    if settings.CLERK_JWT_PUBLIC_KEY:
        return jwt.decode(
            token,
            settings.CLERK_JWT_PUBLIC_KEY,
            algorithms=["RS256"],
            audience=audience,
            issuer=issuer,
            options={"verify_signature": True, "verify_exp": True},
        )

    # 3) No verification material configured.
    #    Fail closed whenever verification is required, or outside development.
    if require_verification or settings.ENVIRONMENT == "production":
        logger.error(
            "Token verification requested but no CLERK_JWT_PUBLIC_KEY / CLERK_JWKS_URL configured."
        )
        raise HTTPException(status_code=401, detail="Authentication is not configured")

    logger.warning(
        "DEV ONLY: decoding Clerk token WITHOUT signature verification "
        "(set CLERK_JWKS_URL or CLERK_JWT_PUBLIC_KEY to enable verification)."
    )
    return jwt.decode(
        token,
        key="",
        options={
            "verify_signature": False,
            "verify_exp": False,
            "verify_aud": False,
            "verify_iss": False,
        },
    )


def extract_user_id_from_token(token: str, require_verification: bool = True) -> str:
    """
    Extract the Clerk user id (``sub``) from a JWT.

    Args:
        token: JWT token string.
        require_verification: When True, the token MUST be cryptographically
            verified. When False, verification is still performed if material is
            configured; only in local development with no material configured is
            an unverified decode allowed.
    """
    try:
        payload = _decode_clerk_token(token, require_verification)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token missing subject")
        return user_id
    except HTTPException:
        raise
    except JWTError:
        # Do not leak library internals to the client.
        logger.info("Clerk JWT validation failed")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    except Exception:
        logger.exception("Unexpected error validating Clerk token")
        raise HTTPException(status_code=401, detail="Could not validate credentials")


def verify_clerk_token(token: str) -> str:
    """Full verification helper (for production code paths)."""
    return extract_user_id_from_token(token, require_verification=True)


def extract_email_from_token(token: str, require_verification: bool = True) -> Optional[str]:
    """Extract a normalized lowercase email from a Clerk JWT, or None."""
    try:
        payload = _decode_clerk_token(token, require_verification)
        email = (
            payload.get("email")
            or payload.get("primary_email")
            or payload.get("primaryEmailAddress")
            or (
                payload.get("email_addresses")
                and len(payload.get("email_addresses", [])) > 0
                and payload.get("email_addresses")[0].get("email_address")
            )
        )
        if not email:
            return None
        return str(email).strip().lower()
    except HTTPException:
        return None
    except Exception:
        return None
