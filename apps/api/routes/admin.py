"""
Admin API Routes

Provides admin-only endpoints for managing users and viewing system-wide metrics.
"""

from fastapi import APIRouter, Request, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import httpx

from packages.core.database.connection import get_db
from packages.core.database.models.user import User
from packages.core.monitoring.metrics import get_metrics_collector
from packages.core.guardrails.cost_manager import get_cost_manager
from apps.api.middleware.auth import extract_user_id_from_token
from config.settings import settings

router = APIRouter()


async def check_admin_role(request: Request, db: AsyncSession) -> bool:
    """
    Check if the current user has admin role.
    
    Returns:
        True if user is admin, False otherwise
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        return False
    
    # Look up user by clerk_user_id
    result = await db.execute(
        select(User).where(User.clerk_user_id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if user:
        return user.role == "admin"
    
    # If not found by clerk_user_id, try to get email from token and check by email
    try:
        # Extract email from token if available
        auth_header = request.headers.get("Authorization", "")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "").strip()
            from jose import jwt
            
            # Decode token to get email
            try:
                payload = jwt.decode(
                    token,
                    key="",
                    options={"verify_signature": False, "verify_exp": False}
                )
                
                # Try multiple possible email fields in token
                email = (
                    payload.get("email") or 
                    payload.get("primary_email") or 
                    payload.get("primaryEmailAddress") or
                    (payload.get("email_addresses") and len(payload.get("email_addresses", [])) > 0 and payload.get("email_addresses")[0].get("email_address"))
                )
                
                if email:
                    # Normalize email
                    email = email.lower().strip()
                    result = await db.execute(
                        select(User).where(User.email == email)
                    )
                    user = result.scalar_one_or_none()
                    
                    if user:
                        # If user found and clerk_user_id is not set, update it
                        if not user.clerk_user_id and user_id:
                            try:
                                user.clerk_user_id = user_id
                                await db.commit()
                            except Exception:
                                await db.rollback()
                        
                        return user.role == "admin"
            except Exception:
                pass
    except Exception:
        pass
    
    return False


@router.get("/users")
async def list_all_users(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    List all users from Clerk (admin only).
    
    Fetches all users from Clerk API and merges with local database roles.
    """
    # Check admin role
    is_admin = await check_admin_role(request, db)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Fetch all users from Clerk
    clerk_users = []
    if settings.CLERK_SECRET_KEY:
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}",
                    "Content-Type": "application/json",
                }
                
                all_clerk_users = []
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
                    elif isinstance(data, dict):
                        users_page = data.get("data", [])
                    else:
                        users_page = []
                    
                    if not users_page:
                        break
                    
                    all_clerk_users.extend(users_page)
                    
                    total_count = None
                    if isinstance(data, dict):
                        total_count = data.get("total_count")
                    
                    if total_count is not None:
                        if len(all_clerk_users) >= total_count:
                            break
                    
                    if len(users_page) < limit:
                        break
                    
                    offset += limit
                
                clerk_users = all_clerk_users
        except Exception:
            pass
    
    # If no Clerk users were fetched, fallback to database users
    if not clerk_users:
        result = await db.execute(select(User))
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
    
    # Get users from database to merge roles
    result = await db.execute(select(User))
    db_users = result.scalars().all()
    
    # Create a map of clerk_user_id -> role
    clerk_id_to_role = {user.clerk_user_id: user.role for user in db_users if user.clerk_user_id}
    email_to_role = {user.email.lower(): user.role for user in db_users}
    
    # Merge Clerk users with database roles
    merged_users = []
    for clerk_user in clerk_users:
        clerk_user_id = clerk_user.get("id")
        email_addresses = clerk_user.get("email_addresses", [])
        
        primary_email = None
        if email_addresses:
            verified_email = next(
                (e.get("email_address") for e in email_addresses if e.get("verification", {}).get("status") == "verified"),
                None
            )
            if verified_email:
                primary_email = verified_email
            else:
                primary_email = email_addresses[0].get("email_address") if email_addresses else None

        # Get role from database (by clerk_user_id or email)
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
    
    return {
        "tenant_id": tenant_id,
        "period_days": days,
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
