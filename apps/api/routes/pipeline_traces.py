"""
Pipeline trace API (LangGraph + RAG debugger).

Traces are in-memory per process. GET /recent is available to any authenticated user
(their traces only); admins see global recent.
"""

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from packages.core.database.connection import get_db
from packages.core.monitoring.pipeline_trace import get_pipeline_trace_store
from apps.api.routes.admin import check_admin_role

router = APIRouter()


@router.get("/recent")
async def list_recent_traces(
    request: Request,
    db: AsyncSession = Depends(get_db),
    limit: int = 30,
) -> Dict[str, Any]:
    """
    Recent pipeline traces for the authenticated user.
    Admins see global recent traces (all users); regular users only their own.
    """
    if not getattr(settings, "ENABLE_PIPELINE_TRACE", True):
        raise HTTPException(status_code=404, detail="Pipeline tracing disabled")
    uid = getattr(request.state, "user_id", None)
    if not uid:
        raise HTTPException(status_code=401, detail="Authentication required")
    is_admin = await check_admin_role(request, db)
    store = get_pipeline_trace_store()
    # None = no filter (admin); else restrict to caller's Clerk user id
    filter_user: str | None = None if is_admin else uid
    traces = store.list_recent_traces_filtered(user_id=filter_user, limit=min(limit, 100))
    out: List[Dict[str, Any]] = [
        {
            "trace_id": tr.trace_id,
            "user_id": tr.user_id,
            "tenant_id": tr.tenant_id,
            "total_duration_ms": tr.total_duration_ms,
            "success": tr.success,
            "span_count": len(tr.spans),
        }
        for tr in traces
    ]
    return {"traces": out, "scope": "all" if is_admin else "mine"}


@router.get("/{trace_id}")
async def get_pipeline_trace(
    trace_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Return a single trace (owner or admin)."""
    if not getattr(settings, "ENABLE_PIPELINE_TRACE", True):
        raise HTTPException(status_code=404, detail="Pipeline tracing disabled")
    uid = getattr(request.state, "user_id", None)
    if not uid:
        raise HTTPException(status_code=401, detail="Authentication required")
    store = get_pipeline_trace_store()
    tr = store.get_trace(trace_id)
    if not tr:
        raise HTTPException(status_code=404, detail="Trace not found or expired")
    # Owner can always load their trace without hitting the DB for admin role.
    if uid == tr.user_id:
        return store.to_jsonable(tr)
    # Cross-tenant / other-user trace: require admin. If DB is down, return 503 — not a
    # misleading 403 (check_admin_role otherwise returns False when DB errors).
    is_admin = await check_admin_role(request, db, raise_on_db_unavailable=True)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Not allowed to view this trace")
    return store.to_jsonable(tr)
