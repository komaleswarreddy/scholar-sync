"""
LlamaIndex adapters

These adapters let us swap LlamaIndex into the existing ScholarSync RAG pipeline
while preserving external contracts (FastAPI routes, SSE event shapes, metadata).
"""

from .ingestion import LlamaIndexIngestionAdapter
from .retrieval import LlamaIndexRetrievalAdapter

__all__ = [
    "LlamaIndexIngestionAdapter",
    "LlamaIndexRetrievalAdapter",
]

