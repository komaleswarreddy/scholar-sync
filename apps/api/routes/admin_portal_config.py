"""Admin-configurable portal tab visibility (tenant-scoped).

Lets a platform admin turn student-portal tabs on/off (e.g. hide Analytics).
Stored in Tenant.settings["enabled_tabs"] — no new table needed.
"""

from __future__ import annotations

import uuid
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.routes.admin import check_admin_role
from packages.core.database.connection import get_db
from packages.core.database.models.tenant import Tenant

TOGGLEABLE_TABS = ["analytics", "study_planner", "problem_solver", "assets"]
DEFAULT_ENABLED_TABS: Dict[str, bool] = {tab: True for tab in TOGGLEABLE_TABS}

# Mounted at /api/v1 — readable by any authenticated tenant user (student portal nav).
public_router = APIRouter()
# Mounted at /api/v1/admin — platform-admin only.
admin_router = APIRouter()


async def _get_tenant(db: AsyncSession, tenant_id: str) -> Tenant:
    result = await db.execute(select(Tenant).where(Tenant.id == uuid.UUID(str(tenant_id))))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


def _resolve_enabled_tabs(tenant: Tenant) -> Dict[str, bool]:
    stored = (tenant.settings or {}).get("enabled_tabs") or {}
    return {**DEFAULT_ENABLED_TABS, **stored}


def _require_tenant(request: Request) -> str:
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Tenant context not found")
    return tenant_id


class PortalConfigUpdate(BaseModel):
    tab: str = Field(..., description="Tab key, e.g. 'analytics'")
    enabled: bool


@public_router.get("/portal-config")
async def get_portal_config(request: Request, db: AsyncSession = Depends(get_db)):
    tenant = await _get_tenant(db, _require_tenant(request))
    return {"enabled_tabs": _resolve_enabled_tabs(tenant)}


@admin_router.get("/portal-config")
async def admin_get_portal_config(request: Request, db: AsyncSession = Depends(get_db)):
    if not await check_admin_role(request, db, raise_on_db_unavailable=True):
        raise HTTPException(status_code=403, detail="Platform admin required")
    tenant = await _get_tenant(db, _require_tenant(request))
    return {"enabled_tabs": _resolve_enabled_tabs(tenant)}


@admin_router.patch("/portal-config")
async def admin_update_portal_config(
    body: PortalConfigUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    if not await check_admin_role(request, db, raise_on_db_unavailable=True):
        raise HTTPException(status_code=403, detail="Platform admin required")
    if body.tab not in TOGGLEABLE_TABS:
        raise HTTPException(status_code=400, detail=f"Unknown tab '{body.tab}'")

    tenant = await _get_tenant(db, _require_tenant(request))
    settings = dict(tenant.settings or {})
    enabled_tabs = dict(settings.get("enabled_tabs") or {})
    enabled_tabs[body.tab] = body.enabled
    settings["enabled_tabs"] = enabled_tabs
    tenant.settings = settings
    await db.commit()

    return {"enabled_tabs": _resolve_enabled_tabs(tenant)}
