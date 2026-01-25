"""
API Routes

FastAPI route handlers for all API endpoints.
"""

from apps.api.routes import chat, sources, studio, notes, health

__all__ = [
    "chat",
    "sources",
    "studio",
    "notes",
    "health",
]
