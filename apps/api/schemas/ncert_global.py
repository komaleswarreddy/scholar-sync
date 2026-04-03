"""Pydantic schemas for NCERT global knowledge admin API."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class NcertGlobalDocumentResponse(BaseModel):
    id: str
    class_num: int
    subject: str
    chapter_no: Optional[int] = None
    chapter_name: Optional[str] = None
    title: str
    original_filename: str
    storage_key: str
    status: str
    chunks_count: int
    error_message: Optional[str] = None
    uploaded_by_clerk_user_id: str
    pinecone_namespace: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NcertGlobalIngestionRunResponse(BaseModel):
    id: str
    document_id: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    context_llm_prompt_tokens: int = 0
    context_llm_completion_tokens: int = 0
    context_llm_cost_usd: float = 0.0
    embedding_prompt_tokens: int = 0
    embedding_cost_usd: float = 0.0
    total_cost_usd: float = 0.0
    chunks_processed: int = 0
    error_message: Optional[str] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_run(cls, run) -> "NcertGlobalIngestionRunResponse":
        def _f(v) -> float:
            if v is None:
                return 0.0
            if isinstance(v, Decimal):
                return float(v)
            return float(v)

        return cls(
            id=str(run.id),
            document_id=str(run.document_id),
            status=run.status,
            started_at=run.started_at,
            completed_at=run.completed_at,
            context_llm_prompt_tokens=int(run.context_llm_prompt_tokens or 0),
            context_llm_completion_tokens=int(run.context_llm_completion_tokens or 0),
            context_llm_cost_usd=_f(run.context_llm_cost_usd),
            embedding_prompt_tokens=int(run.embedding_prompt_tokens or 0),
            embedding_cost_usd=_f(run.embedding_cost_usd),
            total_cost_usd=_f(run.total_cost_usd),
            chunks_processed=int(run.chunks_processed or 0),
            error_message=run.error_message,
        )


class NcertGlobalDocumentListResponse(BaseModel):
    documents: List[NcertGlobalDocumentResponse]
    total: int


class NcertGlobalIngestionRunListResponse(BaseModel):
    runs: List[NcertGlobalIngestionRunResponse]
    total: int


class NcertGlobalUploadAcceptedResponse(BaseModel):
    document: NcertGlobalDocumentResponse
    ingestion_run_id: str
    message: str = "Upload accepted; processing in background."
