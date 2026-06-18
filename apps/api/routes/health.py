"""
Health Check Endpoint

Simple health check endpoint for monitoring and load balancers.
"""

from fastapi import APIRouter, Request

from config.settings import settings
from packages.core.monitoring.langsmith_bootstrap import configure_langsmith_tracing

router = APIRouter()


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@router.get("/health/langsmith")
async def health_langsmith(request: Request):
    """LangSmith tracing configuration and API connectivity."""
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
    except Exception as exc:
        payload["api_error"] = str(exc)[:240]

    return payload


@router.get("/")
async def root():
    """Root endpoint."""
    return {"message": "ScholarSync API running"}
