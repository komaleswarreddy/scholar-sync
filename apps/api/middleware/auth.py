"""
Authentication Middleware

Handles JWT token extraction and verification for Clerk authentication.
"""

from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from fastapi import HTTPException
import traceback
from config.settings import settings
from typing import Optional


def create_admin_portal_token() -> tuple[str, int]:
    """Issue HS256 JWT for standalone admin portal login."""
    ttl_hours = max(1, int(settings.ADMIN_PORTAL_TOKEN_TTL_HOURS))
    expires_in = ttl_hours * 3600
    exp = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    payload = {
        "sub": settings.ADMIN_PORTAL_USER_ID,
        "admin_portal": True,
        "exp": exp,
    }
    token = jwt.encode(payload, settings.ADMIN_PORTAL_JWT_SECRET, algorithm="HS256")
    return token, expires_in


def extract_admin_portal_user_id(token: str) -> Optional[str]:
    """Return admin portal user id when token is a valid admin portal JWT."""
    if not token or not settings.ADMIN_PORTAL_JWT_SECRET:
        return None
    try:
        payload = jwt.decode(
            token,
            settings.ADMIN_PORTAL_JWT_SECRET,
            algorithms=["HS256"],
        )
        if payload.get("admin_portal") and payload.get("sub"):
            return str(payload["sub"])
    except JWTError:
        return None
    return None


def extract_user_id_from_token(token: str, require_verification: bool = True) -> str:
    """
    Extracts user ID from Clerk JWT token.
    
    Args:
        token: JWT token string
        require_verification: If True, fully verify the token. If False, decode without verification (dev mode only).
    
    Returns:
        User ID (sub claim from token)
    
    Raises:
        HTTPException: If token is invalid or missing user ID
    """
    try:
        if require_verification and settings.CLERK_JWT_PUBLIC_KEY:
            # Full verification with public key (production mode)
            payload = jwt.decode(
                token,
                settings.CLERK_JWT_PUBLIC_KEY,
                algorithms=["RS256"],
                audience=settings.CLERK_JWT_AUDIENCE if settings.CLERK_JWT_AUDIENCE else None,
                issuer=settings.CLERK_ISSUER if settings.CLERK_ISSUER else None,
                options={"verify_signature": True}
            )
        else:
            # Decode without verification (dev mode only - for testing)
            # WARNING: This should only be used in development!
            # We still need to provide a key, but we skip signature verification
            payload = jwt.decode(
                token,
                key="",  # Empty key since we're not verifying
                options={"verify_signature": False, "verify_exp": False, "verify_aud": False, "verify_iss": False}
            )
        
        user_id = payload.get("sub")
        if not user_id:
            print("AUTH ERROR: Token payload missing 'sub' claim.")
            raise HTTPException(status_code=401, detail="Token missing subject")
            
        return user_id

    except JWTError as e:
        print(f"JWT VERIFICATION ERROR: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {str(e)}")
    except Exception as e:
        print(f"CRITICAL AUTH ERROR: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=401, detail="Could not validate credentials")


def verify_clerk_token(token: str) -> str:
    """
    Verifies a Clerk JWT token and returns the user's ID (the 'sub' claim).
    This is the full verification method (for production).
    """
    return extract_user_id_from_token(token, require_verification=True)


def extract_email_from_token(token: str, require_verification: bool = True) -> Optional[str]:
    """
    Extract user email from Clerk JWT token.

    Returns normalized lowercase email when present, else None.
    """
    try:
        if require_verification and settings.CLERK_JWT_PUBLIC_KEY:
            payload = jwt.decode(
                token,
                settings.CLERK_JWT_PUBLIC_KEY,
                algorithms=["RS256"],
                audience=settings.CLERK_JWT_AUDIENCE if settings.CLERK_JWT_AUDIENCE else None,
                issuer=settings.CLERK_ISSUER if settings.CLERK_ISSUER else None,
                options={"verify_signature": True},
            )
        else:
            payload = jwt.decode(
                token,
                key="",
                options={"verify_signature": False, "verify_exp": False, "verify_aud": False, "verify_iss": False},
            )

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
    except Exception:
        return None


