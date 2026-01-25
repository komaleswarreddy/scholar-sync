"""
Base Schemas

Common base classes and utilities for API schemas.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class BaseResponse(BaseModel):
    """Base response schema with common fields."""
    success: bool = True
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseResponse):
    """Error response schema."""
    success: bool = False
    error_code: Optional[str] = None
    detail: str


