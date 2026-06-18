"""Studio feature API schemas."""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class StudioFeatureCreateRequest(BaseModel):
    notebook_id: str
    type: str
    title: str
    content: Any
    source_ids: Optional[List[str]] = None


class StudioFeatureResponse(BaseModel):
    id: str
    notebook_id: str
    type: str
    title: str
    content: Any
    source_ids: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class StudioFeatureListResponse(BaseModel):
    features: List[StudioFeatureResponse]
    total: int
