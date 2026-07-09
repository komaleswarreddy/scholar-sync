"""
Admin API Routes

Provides admin-only endpoints for managing users and viewing system-wide metrics.
"""

from fastapi import APIRouter, Request, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import DBAPIError, OperationalError
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import asyncio
import hmac
import httpx
import time
import uuid

from packages.core.database.connection import get_db
from packages.core.database.models.user import User
from packages.core.database.models.chat import Chat, Message
from packages.core.monitoring.metrics import get_metrics_collector
from packages.core.guardrails.cost_manager import get_cost_manager
from apps.api.middleware.auth import (
    extract_user_id_from_token,
    create_admin_portal_token,
    verify_portal_password,
)
from apps.api.middleware.login_guard import (
    check_login_allowed,
    record_failure,
    record_success,
)
from apps.api.utils.safe_errors import safe_detail
from config.settings import settings
from sqlalchemy import func


class AdminPortalLoginRequest(BaseModel):
    email: str
    password: str

router = APIRouter()
_admin_role_cache: Dict[str, tuple[bool, float]] = {}
# Cache admin role longer to reduce DB dependency for read-only admin UX (analytics, pipeline traces).
# This is safe because role changes are rare; if roles are edited, a short delay is acceptable.
_ADMIN_ROLE_CACHE_TTL_S = 10 * 60.0

_users_list_cache: Dict[str, tuple[dict, float]] = {}
_USERS_LIST_CACHE_TTL_S = 45.0


def invalidate_users_list_cache(tenant_id: str | None = None) -> None:
    if tenant_id:
        _users_list_cache.pop(str(tenant_id), None)
    else:
        _users_list_cache.clear()


def _is_db_unavailable_error(exc: Exception) -> bool:
    if isinstance(exc, (OperationalError, DBAPIError, OSError, TimeoutError)):
        return True
    msg = str(exc).lower()
    return (
        "connect call failed" in msg
        or "database connection error" in msg
        or "could not connect" in msg
        or "connection refused" in msg
        or "maxclientsinsessionmode" in msg
        or "max clients reached" in msg
        or "too many connections" in msg
        or "timeout" in msg
    )


def _extract_primary_email(clerk_user: Dict[str, Any]) -> Optional[str]:
    """Pick a stable primary email from Clerk user payload."""
    email_addresses = clerk_user.get("email_addresses", []) or []
    if not email_addresses:
        return None
    verified_email = next(
        (e.get("email_address") for e in email_addresses if (e.get("verification") or {}).get("status") == "verified"),
        None,
    )
    email = verified_email or email_addresses[0].get("email_address")
    if not email:
        return None
    return str(email).strip().lower()


async def _fetch_all_clerk_users() -> List[Dict[str, Any]]:
    """Fetch all Clerk users with pagination."""
    if not settings.CLERK_SECRET_KEY:
        return []
    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}",
            "Content-Type": "application/json",
        }
        all_clerk_users: List[Dict[str, Any]] = []
        limit = 500
        offset = 0
        while True:
            response = await client.get(
                "https://api.clerk.com/v1/users",
                headers=headers,
                params={"limit": limit, "offset": offset},
                timeout=30.0,
            )
            if response.status_code != 200:
                break
            data = response.json()
            if isinstance(data, list):
                users_page = data
                total_count = None
            elif isinstance(data, dict):
                users_page = data.get("data", [])
                total_count = data.get("total_count")
            else:
                users_page = []
                total_count = None
            if not users_page:
                break
            all_clerk_users.extend(users_page)
            if total_count is not None and len(all_clerk_users) >= int(total_count):
                break
            if len(users_page) < limit:
                break
            offset += limit
        return all_clerk_users


async def check_admin_role(
    request: Request,
    db: AsyncSession,
    *,
    raise_on_db_unavailable: bool = False,
    db_timeout_s: float = 3.0,
) -> bool:
    """
    Check if the current user has schooladmin role (or bootstrap admin).
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        return False

    # Bootstrap admin from env credentials
    if user_id == settings.ADMIN_PORTAL_USER_ID:
        _admin_role_cache[user_id] = (True, time.monotonic() + _ADMIN_ROLE_CACHE_TTL_S)
        return True

    now = time.monotonic()

    # JWT role claim (platform token)
    jwt_role = getattr(request.state, "user_role", None)
    if jwt_role == "schooladmin":
        _admin_role_cache[user_id] = (True, now + _ADMIN_ROLE_CACHE_TTL_S)
        return True
    if jwt_role and jwt_role != "schooladmin":
        _admin_role_cache[user_id] = (False, now + _ADMIN_ROLE_CACHE_TTL_S)
        return False

    cached = _admin_role_cache.get(user_id)
    if cached and cached[1] > now:
        return bool(cached[0])

    # Look up user by UUID id
    try:
        uid = uuid.UUID(str(user_id))
    except ValueError:
        _admin_role_cache[user_id] = (False, now + _ADMIN_ROLE_CACHE_TTL_S)
        return False

    try:
        result = await asyncio.wait_for(
            db.execute(select(User).where(User.id == uid)),
            timeout=db_timeout_s,
        )
        user = result.scalar_one_or_none()
    except Exception as e:
        if _is_db_unavailable_error(e):
            if cached:
                return bool(cached[0])
            if raise_on_db_unavailable:
                raise HTTPException(
                    status_code=503,
                    detail="Database unavailable. Please check DATABASE_URL and try again.",
                )
            return False
        raise

    is_admin = bool(user and user.role == "schooladmin" and user.is_active)
    _admin_role_cache[user_id] = (is_admin, now + _ADMIN_ROLE_CACHE_TTL_S)
    return is_admin


@router.post("/auth/login")
async def admin_portal_login(body: AdminPortalLoginRequest, request: Request):
    """
    Standalone admin portal login (email/password).
    Returns a Bearer JWT for ops dashboard API calls — not a Clerk session.

    Hardening: per-IP+email rate limiting/lockout, constant-time password
    comparison, and support for a bcrypt password hash.
    """
    email = (body.email or "").strip().lower()
    password = body.password or ""
    expected_email = (settings.ADMIN_PORTAL_EMAIL or "").strip().lower()

    check_login_allowed("admin", request, email)

    email_ok = hmac.compare_digest(email.encode("utf-8"), expected_email.encode("utf-8"))
    password_ok = await verify_portal_password(
        password, settings.ADMIN_PORTAL_PASSWORD, settings.ADMIN_PORTAL_PASSWORD_HASH
    )
    if not (email_ok and password_ok):
        record_failure("admin", request, email)
        # Generic message — do not reveal which field was wrong.
        raise HTTPException(status_code=401, detail="Invalid email or password")

    record_success("admin", request, email)
    access_token, expires_in = create_admin_portal_token()
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": expires_in,
    }


@router.get("/users")
async def list_all_users(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    List users for the admin dashboard.

    Platform auth (default): tenant-scoped rows from PostgreSQL — no Clerk round-trip.
    Legacy Clerk merge only when CLERK_LEGACY_USER_SYNC=true and CLERK_SECRET_KEY is set.
    """
    is_admin = await check_admin_role(request, db, raise_on_db_unavailable=True)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    tenant_id = getattr(request.state, "tenant_id", None)
    cache_key = str(tenant_id) if tenant_id else "all"
    now = time.monotonic()
    cached_payload = _users_list_cache.get(cache_key)
    if cached_payload and cached_payload[1] > now:
        return cached_payload[0]

    query = select(User)
    if tenant_id:
        try:
            query = query.where(User.tenant_id == uuid.UUID(str(tenant_id)))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid tenant")

    # Fast path: platform users only (no external Clerk API — was causing 5–30s delays)
    if not (settings.CLERK_LEGACY_USER_SYNC and settings.CLERK_SECRET_KEY):
        try:
            result = await asyncio.wait_for(db.execute(query.order_by(User.created_at.desc())), timeout=8.0)
        except Exception as e:
            if _is_db_unavailable_error(e):
                raise HTTPException(
                    status_code=503,
                    detail="Database unavailable while listing users. Please check DATABASE_URL and try again.",
                )
            raise
        db_users = result.scalars().all()
        payload = {
            "users": [
                {
                    "id": str(user.id),
                    "clerk_user_id": user.clerk_user_id or str(user.id),
                    "email": user.email,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role or "student",
                    "is_active": bool(user.is_active),
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "last_sign_in_at": None,
                }
                for user in db_users
            ],
            "total": len(db_users),
        }
        _users_list_cache[cache_key] = (payload, now + _USERS_LIST_CACHE_TTL_S)
        return payload

    # Legacy Clerk merge (opt-in only)
    clerk_users: List[Dict[str, Any]] = []
    try:
        clerk_users = await _fetch_all_clerk_users()
    except Exception:
        pass

    if not clerk_users:
        try:
            result = await asyncio.wait_for(db.execute(query), timeout=8.0)
        except Exception as e:
            if _is_db_unavailable_error(e):
                raise HTTPException(
                    status_code=503,
                    detail="Database unavailable while listing users. Please check DATABASE_URL and try again.",
                )
            raise
        db_users = result.scalars().all()
        return {
            "users": [
                {
                    "id": str(user.id),
                    "email": user.email,
                    "clerk_user_id": user.clerk_user_id,
                    "role": user.role,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                }
                for user in db_users
            ],
            "total": len(db_users),
        }

    try:
        result = await asyncio.wait_for(db.execute(query), timeout=8.0)
    except Exception as e:
        if _is_db_unavailable_error(e):
            raise HTTPException(
                status_code=503,
                detail="Database unavailable while merging user roles. Please check DATABASE_URL and try again.",
            )
        raise
    db_users = result.scalars().all()

    clerk_id_to_role = {user.clerk_user_id: user.role for user in db_users if user.clerk_user_id}
    email_to_role = {user.email.lower(): user.role for user in db_users if user.email}

    merged_users = []
    for clerk_user in clerk_users:
        clerk_user_id = clerk_user.get("id")
        primary_email = _extract_primary_email(clerk_user)

        role = "user"
        if clerk_user_id and clerk_user_id in clerk_id_to_role:
            role = clerk_id_to_role[clerk_user_id]
        elif primary_email and primary_email.lower() in email_to_role:
            role = email_to_role[primary_email.lower()]

        merged_users.append({
            "id": clerk_user_id,
            "clerk_user_id": clerk_user_id,
            "email": primary_email,
            "first_name": clerk_user.get("first_name"),
            "last_name": clerk_user.get("last_name"),
            "username": clerk_user.get("username"),
            "role": role,
            "created_at": clerk_user.get("created_at"),
            "last_sign_in_at": clerk_user.get("last_sign_in_at"),
        })

    return {
        "users": merged_users,
        "total": len(merged_users),
    }


@router.post("/users/backfill")
async def backfill_users_from_clerk(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    One-time backfill: import all Clerk users into local users table.
    Also fixes malformed placeholder emails (e.g. '{{...}}').
    """
    is_admin = await check_admin_role(request, db)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    if not settings.CLERK_SECRET_KEY:
        raise HTTPException(status_code=400, detail="CLERK_SECRET_KEY is not configured")

    try:
        clerk_users = await _fetch_all_clerk_users()
    except Exception as e:
        raise HTTPException(status_code=502, detail=safe_detail(e, "Failed to fetch users from Clerk"))

    if not clerk_users:
        return {
            "ok": True,
            "message": "No users returned by Clerk.",
            "stats": {
                "clerk_total": 0,
                "inserted": 0,
                "updated": 0,
                "email_fixed": 0,
                "skipped_no_email": 0,
            },
        }

    inserted = 0
    updated = 0
    email_fixed = 0
    skipped_no_email = 0

    db_users_res = await db.execute(select(User))
    db_users = db_users_res.scalars().all()
    by_clerk: Dict[str, User] = {u.clerk_user_id: u for u in db_users if u.clerk_user_id}
    by_email: Dict[str, User] = {str(u.email).strip().lower(): u for u in db_users if u.email}

    for cu in clerk_users:
        clerk_user_id = str(cu.get("id") or "").strip()
        email = _extract_primary_email(cu)
        if not email:
            skipped_no_email += 1
            continue

        row = by_clerk.get(clerk_user_id) if clerk_user_id else None
        if row is None:
            row = by_email.get(email)

        if row is None:
            role = "user"
            new_row = User(
                id=uuid.uuid4(),
                email=email,
                clerk_user_id=clerk_user_id or None,
                role=role,
            )
            db.add(new_row)
            inserted += 1
            if clerk_user_id:
                by_clerk[clerk_user_id] = new_row
            by_email[email] = new_row
            continue

        changed = False
        if clerk_user_id and not row.clerk_user_id:
            row.clerk_user_id = clerk_user_id
            changed = True

        existing_email = str(row.email or "").strip().lower()
        is_placeholder = ("{{" in existing_email) or ("}}" in existing_email) or ("user.primary_email_address" in existing_email)
        if (not existing_email or is_placeholder) and email:
            row.email = email
            changed = True
            email_fixed += 1
        elif existing_email != email and is_placeholder:
            row.email = email
            changed = True
            email_fixed += 1

        if changed:
            updated += 1

        if clerk_user_id:
            by_clerk[clerk_user_id] = row
        by_email[email] = row

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=safe_detail(e, "Failed to persist backfill"))

    return {
        "ok": True,
        "message": "Backfill completed.",
        "stats": {
            "clerk_total": len(clerk_users),
            "inserted": inserted,
            "updated": updated,
            "email_fixed": email_fixed,
            "skipped_no_email": skipped_no_email,
        },
    }


@router.get("/me/flags")
async def get_my_flags(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Lightweight UI flags (200 when authenticated, never 403).
    Use this instead of probing admin-only routes to detect sidebar role.
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")
    is_admin = await check_admin_role(request, db)
    return {"is_admin": is_admin}


@router.get("/me/metrics")
async def get_my_metrics(
    request: Request,
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, description="Number of days to analyze"),
):
    """
    Get detailed metrics for the current user (no admin required).
    
    Returns:
    - Token consumption
    - Cost breakdown
    - Latency metrics
    - Cache efficiency
    - Endpoint usage
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")
    
    tenant_id = request.state.tenant_id
    metrics = get_metrics_collector()
    cost_manager = get_cost_manager()
    
    # Get metrics summary for this user
    summary = metrics.get_metrics_summary(tenant_id=tenant_id, user_id=user_id)
    
    # Get usage summary
    usage_summary = await cost_manager.get_usage_summary(tenant_id=tenant_id, user_id=user_id)
    
    # Get endpoint usage breakdown
    with metrics._lock:
        llm_calls = list(metrics._llm_calls)
        if tenant_id:
            llm_calls = [m for m in llm_calls if str(m.get("tenant_id")) == str(tenant_id)]
        if user_id:
            llm_calls = [m for m in llm_calls if str(m.get("user_id")) == str(user_id)]
    
    # Group by endpoint/feature
    endpoint_usage: Dict[str, Dict[str, Any]] = {}
    for call in llm_calls:
        endpoint = call.get("feature_tag", "unknown")
        if endpoint not in endpoint_usage:
            endpoint_usage[endpoint] = {
                "endpoint": endpoint,
                "total_calls": 0,
                "total_tokens": 0,
                "total_cost": 0,
                "latencies": [],
            }
        
        endpoint_usage[endpoint]["total_calls"] += 1
        endpoint_usage[endpoint]["total_tokens"] += call.get("total_tokens", 0)
        endpoint_usage[endpoint]["total_cost"] += call.get("cost", 0)
        if call.get("latency_ms"):
            endpoint_usage[endpoint]["latencies"].append(call.get("latency_ms"))
    
    # Calculate averages
    endpoints = []
    for endpoint_data in endpoint_usage.values():
        avg_latency = (
            sum(endpoint_data["latencies"]) / len(endpoint_data["latencies"])
            if endpoint_data["latencies"]
            else None
        )
        endpoints.append({
            "endpoint": endpoint_data["endpoint"],
            "total_calls": endpoint_data["total_calls"],
            "total_tokens": endpoint_data["total_tokens"],
            "total_cost": endpoint_data["total_cost"],
            "avg_latency": avg_latency,
        })
    
    endpoints.sort(key=lambda x: x["total_tokens"], reverse=True)
    
    # Get RAG quality for this user
    from apps.api.routes.metrics import get_rag_quality_dashboard
    
    class UserRequest:
        def __init__(self, tenant_id, user_id):
            self.state = type('obj', (object,), {'tenant_id': tenant_id, 'user_id': user_id})()
    
    mock_request = UserRequest(tenant_id, user_id)
    rag_quality_data = await get_rag_quality_dashboard(mock_request, db, days)
    
    return {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "summary": summary,
        "usage": usage_summary,
        "endpoints": endpoints,
        "rag_quality": rag_quality_data,
    }


@router.get("/users/{user_id}/metrics")
async def get_user_metrics(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, description="Number of days to analyze"),
):
    """
    Get detailed metrics for a specific user (admin only).
    
    Returns:
    - Token consumption
    - Cost breakdown
    - Latency metrics
    - Cache efficiency
    - Endpoint usage
    """
    # Check admin role
    is_admin = await check_admin_role(request, db)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    tenant_id = request.state.tenant_id
    metrics = get_metrics_collector()
    cost_manager = get_cost_manager()
    
    # Get metrics summary for this user
    summary = metrics.get_metrics_summary(tenant_id=tenant_id, user_id=user_id)
    
    # Get usage summary
    usage_summary = await cost_manager.get_usage_summary(tenant_id=tenant_id, user_id=user_id)
    
    # Get endpoint usage breakdown
    with metrics._lock:
        llm_calls = list(metrics._llm_calls)
        if tenant_id:
            llm_calls = [m for m in llm_calls if str(m.get("tenant_id")) == str(tenant_id)]
        if user_id:
            llm_calls = [m for m in llm_calls if str(m.get("user_id")) == str(user_id)]
    
    # Group by endpoint/feature
    endpoint_usage: Dict[str, Dict[str, Any]] = {}
    for call in llm_calls:
        endpoint = call.get("feature_tag", "unknown")
        if endpoint not in endpoint_usage:
            endpoint_usage[endpoint] = {
                "endpoint": endpoint,
                "total_calls": 0,
                "total_tokens": 0,
                "total_cost": 0,
                "latencies": [],
            }
        
        endpoint_usage[endpoint]["total_calls"] += 1
        endpoint_usage[endpoint]["total_tokens"] += call.get("total_tokens", 0)
        endpoint_usage[endpoint]["total_cost"] += call.get("cost", 0)
        if call.get("latency_ms"):
            endpoint_usage[endpoint]["latencies"].append(call.get("latency_ms"))
    
    # Calculate averages
    endpoints = []
    for endpoint_data in endpoint_usage.values():
        avg_latency = (
            sum(endpoint_data["latencies"]) / len(endpoint_data["latencies"])
            if endpoint_data["latencies"]
            else None
        )
        endpoints.append({
            "endpoint": endpoint_data["endpoint"],
            "total_calls": endpoint_data["total_calls"],
            "total_tokens": endpoint_data["total_tokens"],
            "total_cost": endpoint_data["total_cost"],
            "avg_latency": avg_latency,
        })
    
    endpoints.sort(key=lambda x: x["total_tokens"], reverse=True)
    
    return {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "summary": summary,
        "usage": usage_summary,
        "endpoints": endpoints,
    }


@router.get("/users/{user_id}/sessions")
async def get_user_sessions(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, description="Number of days to analyze"),
):
    """
    Get session data for a specific user (admin only).
    
    Returns chat sessions with login/logout times.
    Each chat is treated as a session, with created_at as login time
    and last message timestamp as logout time.
    """
    # Check admin role
    is_admin = await check_admin_role(request, db)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    tenant_id = request.state.tenant_id
    tenant_uuid = uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
    
    # Calculate date range
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Get all chats for this user
    chats_result = await db.execute(
        select(Chat)
        .where(Chat.tenant_id == tenant_uuid)
        .where(Chat.user_id == user_id)
        .where(Chat.created_at >= cutoff_date)
        .order_by(Chat.created_at.desc())
    )
    chats = chats_result.scalars().all()
    
    # Get metrics collector to calculate token consumption per session
    from packages.core.monitoring.metrics import get_metrics_collector
    metrics = get_metrics_collector()
    
    # Get all LLM calls for this user and tenant
    with metrics._lock:
        user_llm_calls = []
        for call in metrics._llm_calls:
            # Check tenant match
            if str(call.get("tenant_id")) != str(tenant_id):
                continue
            # Check user match
            if str(call.get("user_id")) != str(user_id):
                continue
            user_llm_calls.append(call)
    
    # Get last message timestamp for each chat and calculate token consumption
    sessions = []
    for chat in chats:
        # Get last message in this chat
        last_message_result = await db.execute(
            select(Message)
            .where(Message.chat_id == chat.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_message = last_message_result.scalar_one_or_none()
        
        login_time = chat.created_at
        logout_time = last_message.created_at if last_message else None
        
        # Calculate duration if logout time exists
        duration = None
        if logout_time:
            duration_ms = (logout_time - login_time).total_seconds() * 1000
            if duration_ms < 60000:
                duration = f"{duration_ms / 1000:.1f}s"
            elif duration_ms < 3600000:
                duration = f"{duration_ms / 60000:.1f}min"
            else:
                duration = f"{duration_ms / 3600000:.1f}h"
        
        # Get message count
        message_count_result = await db.execute(
            select(func.count(Message.id))
            .where(Message.chat_id == chat.id)
        )
        message_count = message_count_result.scalar() or 0
        
        # Calculate token consumption for this session
        # Match LLM calls that occurred during this session's time range
        session_token_consumption = 0
        session_start = login_time
        session_end = logout_time if logout_time else datetime.utcnow()
        
        # Ensure session_end is timezone-aware if session_start is
        if session_start and session_start.tzinfo and not session_end.tzinfo:
            from datetime import timezone
            session_end = session_end.replace(tzinfo=timezone.utc)
        elif session_start and not session_start.tzinfo and session_end.tzinfo:
            session_start = session_start.replace(tzinfo=session_end.tzinfo)
        
        for call in user_llm_calls:
            try:
                call_timestamp = call.get("timestamp", "")
                if not call_timestamp:
                    continue
                call_time = datetime.fromisoformat(call_timestamp.replace('Z', '+00:00'))
                
                # Make timezone-aware if needed
                if call_time.tzinfo is None:
                    from datetime import timezone
                    call_time = call_time.replace(tzinfo=timezone.utc)
                if session_start.tzinfo is None:
                    from datetime import timezone
                    session_start = session_start.replace(tzinfo=timezone.utc)
                if session_end.tzinfo is None:
                    from datetime import timezone
                    session_end = session_end.replace(tzinfo=timezone.utc)
                
                # Check if call occurred during this session
                if session_start <= call_time <= session_end:
                    session_token_consumption += call.get("total_tokens", 0)
            except Exception as e:
                # Skip calls with invalid timestamps
                continue
        
        sessions.append({
            "session_id": str(chat.id),
            "login_time": login_time.isoformat() if login_time else None,
            "logout_time": logout_time.isoformat() if logout_time else None,
            "duration": duration,
            "message_count": message_count,
            "token_consumption": session_token_consumption,
        })
    
    return {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "period_days": days,
        "sessions": sessions,
        "total_sessions": len(sessions),
    }


@router.get("/aggregate")
async def get_aggregate_metrics(
    request: Request,
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, description="Number of days to analyze"),
):
    """
    Get aggregate metrics across all users (admin only).
    
    Returns system-wide metrics including:
    - Total tokens, costs, latency
    - Total users
    - RAG quality
    """
    # Check admin role
    is_admin = await check_admin_role(request, db)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    tenant_id = request.state.tenant_id
    metrics = get_metrics_collector()
    cost_manager = get_cost_manager()
    
    # Get aggregate metrics (no user_id filter)
    summary = metrics.get_metrics_summary(tenant_id=tenant_id, user_id=None)
    usage_summary = await cost_manager.get_usage_summary(tenant_id=tenant_id, user_id=None)
    
    # Get cache hit rate
    cache_hit_rate = metrics.get_cache_hit_rate(tenant_id=tenant_id, user_id=None)
    
    # Get total users from Clerk
    clerk_total_users = 0
    if settings.CLERK_SECRET_KEY:
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}",
                    "Content-Type": "application/json",
                }
                response = await client.get(
                    "https://api.clerk.com/v1/users",
                    headers=headers,
                    params={"limit": 1},
                    timeout=10.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, dict) and "total_count" in data:
                        clerk_total_users = data["total_count"]
                    elif isinstance(data, list):
                        # If it's a list, we'd need to paginate to get total
                        pass
        except Exception:
            pass
    
    # Get active user IDs (users with metrics in the last 30 days)
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    with metrics._lock:
        llm_calls = list(metrics._llm_calls)
        if tenant_id:
            llm_calls = [m for m in llm_calls if str(m.get("tenant_id")) == str(tenant_id)]
    
    active_user_ids = set()
    for call in llm_calls:
        try:
            call_time = datetime.fromisoformat(call.get("timestamp", ""))
            if call_time >= cutoff_date:
                user_id = call.get("user_id")
                if user_id:
                    active_user_ids.add(user_id)
        except Exception:
            continue
    
    # Get aggregate RAG quality (no user_id filter)
    from apps.api.routes.metrics import get_rag_quality_dashboard
    
    class AggregateRequest:
        def __init__(self, tenant_id):
            self.state = type('obj', (object,), {'tenant_id': tenant_id})()
    
    mock_request = AggregateRequest(tenant_id)
    rag_quality_data = await get_rag_quality_dashboard(mock_request, db, days)

    from packages.core.guardrails.budget_enforcer import BudgetEnforcer

    budget_status = BudgetEnforcer().budget_status(str(tenant_id))
    
    return {
        "tenant_id": tenant_id,
        "period_days": days,
        "budget": budget_status,
        "metrics": {
            **summary,
            "cache": {
                **summary.get("cache", {}),
                "hit_rate": cache_hit_rate,
            }
        },
        "usage": usage_summary,
        "users": {
            "total": clerk_total_users,
            "active": len(active_user_ids),
        },
        "rag_quality": rag_quality_data,
    }
