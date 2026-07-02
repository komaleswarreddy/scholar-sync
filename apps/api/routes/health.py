"""
Health Check Endpoint

Simple health check endpoint for monitoring and load balancers.
"""

import logging

from fastapi import APIRouter, HTTPException, Request

from config.settings import settings
from packages.core.monitoring.langsmith_bootstrap import configure_langsmith_tracing

router = APIRouter()
logger = logging.getLogger("scholarsync.health")


@router.get("/health")
async def health():
    """Shallow health check for load balancers (no internal details)."""
    return {"status": "ok"}


@router.get("/health/langsmith")
async def health_langsmith(request: Request):
    """
    LangSmith tracing diagnostics.

    This exposes internal project/endpoint configuration and connectivity, so it
    is restricted to development. In production it returns 404 to avoid
    information disclosure to unauthenticated callers.
    """
    if settings.ENVIRONMENT == "production":
        raise HTTPException(status_code=404, detail="Not found")

    status = getattr(request.app.state, "langsmith", None) or configure_langsmith_tracing()
    payload = {
        "tracing_enabled": bool(status.get("enabled")),
        "project": status.get("project") or settings.LANGSMITH_PROJECT,
        "endpoint": status.get("endpoint") or settings.LANGSMITH_ENDPOINT,
        "api_reachable": False,
        "recent_runs": 0,
    }

    if not payload["tracing_enabled"]:
        payload["message"] = "Set LANGSMITH_TRACING_ENABLED=true and LANGSMITH_API_KEY in .env"
        return payload

    try:
        from langsmith import Client

        client = Client()
        runs = list(
            client.list_runs(
                project_name=payload["project"],
                limit=5,
                is_root=True,
            )
        )
        payload["api_reachable"] = True
        payload["recent_runs"] = len(runs)
        if runs:
            payload["latest_run"] = {
                "id": str(runs[0].id),
                "name": runs[0].name,
                "status": runs[0].status,
            }
    except Exception:
        # Log internally; do not leak the raw error to the caller.
        logger.warning("LangSmith health probe failed", exc_info=True)
        payload["api_error"] = "unavailable"

    return payload


@router.get("/")
async def root():
    """Root endpoint."""
    return {"message": "ScholarSync API running"}
