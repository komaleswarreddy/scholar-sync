"""
Local Storage Implementation

Handles file operations using local filesystem.
For development/testing purposes.
"""

from pathlib import Path
from fastapi import UploadFile
from typing import Optional
import os

from packages.core.storage.base import BaseStorage


class LocalStorage(BaseStorage):
    """
    Local filesystem storage implementation.
    
    Files are stored in: storage/{tenant_id}/{file_path}
    """
    
    def __init__(self, tenant_id: str, base_path: str = "storage"):
        super().__init__(tenant_id)
        self.base_path = Path(base_path)
        self.tenant_path = self.base_path / tenant_id
        self.tenant_path.mkdir(parents=True, exist_ok=True)
    
    async def upload_file(self, file: UploadFile, file_path: str):
        """Upload file to local storage."""
        file_content = await file.read()
        content_type = file.content_type or "application/octet-stream"
        await self.upload_file_bytes(file_content, file_path, content_type)
    
    async def upload_file_bytes(self, file_content: bytes, file_path: str, content_type: str = "application/octet-stream"):
        """Upload file bytes to local storage."""
        full_path = self.tenant_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(file_content)
    
    async def get_presigned_url(self, file_path: str, expiration: int = 3600) -> str:
        """Generate local file URL (not presigned, just path)."""
        full_path = self.tenant_path / file_path
        if full_path.exists():
            return f"/storage/{self.tenant_id}/{file_path}"
        return None
    
    async def download_file(self, file_path: str) -> bytes:
        """Download file from local storage."""
        full_path = self.tenant_path / file_path
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        return full_path.read_bytes()
    
    async def delete_file(self, file_path: str):
        """Delete file from local storage."""
        full_path = self.tenant_path / file_path
        if full_path.exists():
            full_path.unlink()


