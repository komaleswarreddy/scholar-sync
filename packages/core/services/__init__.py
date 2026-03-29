"""
Core services package.

Contains business logic services for ScholarSync.
"""

"""
Avoid importing service modules at package import time.

Some services pull in optional/infra dependencies (S3/Supabase/etc). Importing them
eagerly makes unrelated code paths fail during startup/tests.

Import services directly where needed, e.g.:
  from packages.core.services.studio_service import StudioService
"""

__all__ = ["ChatService", "NotesService", "StudioService", "IngestionService", "SourceService"]

