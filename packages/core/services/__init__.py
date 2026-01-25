"""
Core services package.

Contains business logic services for ScholarSync.
"""

from packages.core.services.chat_service import ChatService
from packages.core.services.note_service import NotesService
from packages.core.services.studio_service import StudioService
from packages.core.services.source_service import IngestionService
from packages.core.services.rag_service import RAGService

__all__ = [
    "ChatService",
    "NotesService",
    "StudioService",
    "IngestionService",
    "RAGService",
]

# Alias for backward compatibility
SourceService = IngestionService

