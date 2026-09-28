"""
Storage package.

Contains storage implementations for file operations.
"""

from packages.core.storage.base import BaseStorage
from packages.core.storage.local import LocalStorage
from packages.core.storage.s3 import S3Storage


def get_storage_service(tenant_id: str) -> BaseStorage:
    """Return the configured storage backend (settings.STORAGE_BACKEND: "s3" | "local")."""
    from config.settings import settings

    if getattr(settings, "STORAGE_BACKEND", "s3").strip().lower() == "local":
        return LocalStorage(tenant_id)
    return S3Storage(tenant_id)


__all__ = [
    "BaseStorage",
    "LocalStorage",
    "S3Storage",
    "get_storage_service",
]


