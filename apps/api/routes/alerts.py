"""
Alerts API

Provides endpoints for viewing alert status and alerts.
"""

from fastapi import APIRouter, Request
from typing import Optional

from packages.core.monitoring.alerts import get_alert_manager

router = APIRouter()


@router.get("/status")
async def get_alerts_status(
    request: Request,
):
    """
    Get alerts status summary.
    
    Returns:
    - Total active alerts
    - Alerts by severity
    - Recent alerts count
    """
    tenant_id = request.state.tenant_id
    
    alert_manager = get_alert_manager()
    alerts = alert_manager.get_recent_alerts(limit=100)
    
    # Filter by tenant if needed
    if tenant_id:
        alerts = [a for a in alerts if a.get("tenant_id") == tenant_id or a.get("tenant_id") is None]
    
    # Count by severity
    severity_counts = {}
    for alert in alerts:
        severity = alert.get("severity", "unknown")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    # Count active alerts (not resolved)
    active_alerts = [a for a in alerts if not a.get("resolved", False)]
    
    return {
        "tenant_id": tenant_id,
        "status": {
            "total_alerts": len(alerts),
            "active_alerts": len(active_alerts),
            "resolved_alerts": len(alerts) - len(active_alerts),
            "by_severity": severity_counts,
        },
        "recent_alerts": alerts[:10],  # Last 10 alerts
    }
