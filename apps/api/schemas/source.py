"""
Source Request/Response Schemas
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Union
from datetime import datetime


class SourceResponse(BaseModel):
    """Response schema for source upload."""
    id: str
    title: str
    status: str = Field(..., description="Status: 'indexed', 'processing', 'error'")
    chunks_count: int = Field(default=0, description="Number of chunks created")
    error_message: Optional[str] = Field(default=None, description="Error message if status is 'error'")
    created_at: datetime
    
    @field_validator('chunks_count', mode='before')
    @classmethod
    def parse_chunks_count(cls, v):
        """Parse chunks_count from string to int."""
        if isinstance(v, str):
            try:
                return int(v)
            except ValueError:
                return 0
        return v or 0


class SourceItem(BaseModel):
    """Source item in list response."""
    id: str
    title: str
    type: str = Field(..., description="Source type: 'pdf', 'text', 'url'")
    created_at: Optional[str] = None  # ISO format string
    s3_url: Optional[str] = None
    status: Optional[str] = Field(default="indexed", description="Status: 'indexed', 'processing', 'error'")
    chunks_count: Optional[int] = Field(default=0, description="Number of chunks created")
    error_message: Optional[str] = Field(default=None, description="Error message if status is 'error'")


class SourceListResponse(BaseModel):
    """Response schema for source list."""
    sources: List[SourceItem]

