"""
Base Storage Interface

Abstract base class for all storage implementations.
"""

from abc import ABC, abstractmethod
from typing import Optional
from fastapi import UploadFile


class BaseStorage(ABC):
    """
    Abstract base class for storage implementations.
    
    All storage providers must implement this interface.
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
    
    @abstractmethod
    async def upload_file(self, file: UploadFile, file_path: str):
        """Upload file to storage."""
        pass
    
    @abstractmethod
    async def upload_file_bytes(self, file_content: bytes, file_path: str, content_type: str = "application/octet-stream"):
        """Upload file bytes to storage."""
        pass
    
    @abstractmethod
    async def get_presigned_url(self, file_path: str, expiration: int = 3600) -> str:
        """Generate presigned URL for file access."""
        pass
    
    @abstractmethod
    async def download_file(self, file_path: str) -> bytes:
        """Download file from storage."""
        pass
    
    @abstractmethod
    async def delete_file(self, file_path: str):
        """Delete file from storage."""
        pass


