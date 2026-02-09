"""
Dashboards API

Alternative path structure for dashboard endpoints.
Provides /api/v1/dashboards/* routes that wrap the metrics endpoints.
"""

from fastapi import APIRouter, Request, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.database.connection import get_db
from apps.api.routes.metrics import (
    get_rag_quality_dashboard,
    get_token_consumption_dashboard,
    get_cost_tracking_dashboard,
    get_cache_efficiency_dashboard,
    get_latency_dashboard,
)

router = APIRouter()


@router.get("/rag-quality")
async def get_rag_quality_dashboard_wrapper(
    request: Request,
    db: AsyncSession = Depends(get_db),
    days: int = Query(7, description="Number of days to analyze"),
):
    """
    RAG Quality Dashboard - Shows hallucination rate and quality metrics.
    
    This endpoint wraps /api/v1/metrics/rag-quality for alternative path structure.
    """
    return await get_rag_quality_dashboard(request, db, days)


@router.get("/tokens")
async def get_token_consumption_dashboard_wrapper(
    request: Request,
    days: int = Query(7, description="Number of days to analyze"),
    group_by: str = Query("feature", description="Group by: 'feature', 'model', 'user'"),
):
    """
    Token Consumption Dashboard - Shows tokens by feature, model, or user.
    
    This endpoint wraps /api/v1/metrics/token-consumption for alternative path structure.
    """
    return await get_token_consumption_dashboard(request, days, group_by)


@router.get("/cost")
async def get_cost_tracking_dashboard_wrapper(
    request: Request,
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, description="Number of days to analyze"),
    group_by_user: bool = Query(False, description="Include per-user breakdown"),
):
    """
    Cost Tracking Dashboard - Shows daily and per-user costs.
    
    This endpoint wraps /api/v1/metrics/cost-tracking for alternative path structure.
    """
    return await get_cost_tracking_dashboard(request, db, days, group_by_user)


@router.get("/cache")
async def get_cache_efficiency_dashboard_wrapper(
    request: Request,
    days: int = Query(7, description="Number of days to analyze"),
):
    """
    Cache Efficiency Dashboard - Shows cache ROI and efficiency metrics.
    
    This endpoint wraps /api/v1/metrics/cache-efficiency for alternative path structure.
    """
    return await get_cache_efficiency_dashboard(request, days)


@router.get("/latency")
async def get_latency_dashboard_wrapper(
    request: Request,
    days: int = Query(7, description="Number of days to analyze"),
):
    """
    Latency Dashboard - Shows latency metrics and identifies bottlenecks.
    
    This endpoint wraps /api/v1/metrics/latency for alternative path structure.
    """
    return await get_latency_dashboard(request, days)
