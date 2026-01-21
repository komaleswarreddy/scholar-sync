"""
Storage Service

Handles file uploads and retrieval from Supabase Storage.
All files are stored in tenant-scoped paths.
"""

from fastapi import UploadFile
from typing import Optional
from supabase import create_client, Client

from app.core.config import settings

# Initialize Supabase client (lazy)
_supabase_client: Optional[Client] = None

def get_supabase_client() -> Client:
    """Get or create Supabase client."""
    global _supabase_client
    if _supabase_client is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            raise ValueError("Supabase URL and Key must be configured")
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _supabase_client


class StorageService:
    """
    Service for Supabase Storage operations.
    
    File paths are tenant-scoped: {tenant_id}/{file_id}.{ext}
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.bucket_name = "scholarsync-files"  # Fixed bucket name
    
    async def upload_file(self, file: UploadFile, file_path: str):
        """
        Upload file to Supabase Storage.
        
        Args:
            file: FastAPI UploadFile object
            file_path: Storage path (e.g., "tenant_id/filename.pdf")
        """
        file_content = await file.read()
        content_type = file.content_type or "application/octet-stream"
        await self.upload_file_bytes(file_content, file_path, content_type)
    
    async def upload_file_bytes(self, file_content: bytes, file_path: str, content_type: str = "application/octet-stream"):
        """
        Upload file bytes to Supabase Storage.
        
        Args:
            file_content: File content as bytes
            file_path: Storage path (e.g., "tenant_id/filename.pdf")
            content_type: MIME type of the file
        """
        try:
            supabase = get_supabase_client()
            
            # Upload to Supabase Storage
            # Note: Supabase Python client is synchronous, so we run it in executor
            import asyncio
            loop = asyncio.get_event_loop()
            
            # Add timeout to prevent hanging (2 minutes)
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: supabase.storage.from_(self.bucket_name).upload(
                        path=file_path,
                        file=file_content,
                        file_options={"content-type": content_type}
                    )
                ),
                timeout=120.0  # 2 minutes timeout
            )
            
            # Check for errors in response
            if hasattr(response, 'error') and response.error:
                print(f"[ERROR] [STORAGE] Supabase returned error: {response.error}")
                raise ValueError(f"Supabase upload error: {response.error}")
                
        except asyncio.TimeoutError:
            print(f"[ERROR] [STORAGE] Upload timeout after 2 minutes for: {file_path}")
            raise ValueError("Storage upload timed out. Please try again.")
        except Exception as e:
            import traceback
            print(f"[ERROR] [STORAGE] Storage upload error: {type(e).__name__}: {str(e)}")
            print(f"[ERROR] [STORAGE] Traceback: {traceback.format_exc()}")
            raise
    
    async def get_presigned_url(self, file_path: str, expiration: int = 3600) -> str:
        """
        Generate presigned URL for file access.
        
        Args:
            file_path: Storage path
            expiration: URL expiration time in seconds
            
        Returns:
            Presigned URL
        """
        supabase = get_supabase_client()
        
        try:
            # Try to create signed URL (for private buckets)
            response = supabase.storage.from_(self.bucket_name).create_signed_url(
                path=file_path,
                expires_in=expiration
            )
            if isinstance(response, dict) and "signedURL" in response:
                return response["signedURL"]
            elif isinstance(response, str):
                return response
            else:
                # Fallback: try to get public URL
                public_url = supabase.storage.from_(self.bucket_name).get_public_url(file_path)
                return public_url
        except Exception as e:
            # Fallback: try to get public URL
            try:
                public_url = supabase.storage.from_(self.bucket_name).get_public_url(file_path)
                return public_url
            except Exception as e2:
                # If all fails, return None (will be handled by caller)
                print(f"Warning: Could not generate URL for {file_path}: {e2}")
                return None
    
    async def download_file(self, file_path: str) -> bytes:
        """
        Download file from Supabase Storage.
        
        Args:
            file_path: Storage path
            
        Returns:
            File content as bytes
        """
        try:
            supabase = get_supabase_client()
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: supabase.storage.from_(self.bucket_name).download(file_path)
            )
            return response
        except Exception as e:
            import traceback
            print(f"[ERROR] Storage download error: {type(e).__name__}: {str(e)}")
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            raise
    
    async def delete_file(self, file_path: str):
        """Delete file from Supabase Storage."""
        try:
            supabase = get_supabase_client()
            import asyncio
            loop = asyncio.get_event_loop()
            
            # Run in executor since Supabase client is synchronous
            response = await loop.run_in_executor(
                None,
                lambda: supabase.storage.from_(self.bucket_name).remove([file_path])
            )
            
            # Check for errors in response
            if hasattr(response, 'error') and response.error:
                print(f"[ERROR] [STORAGE] Supabase delete error: {response.error}")
                raise ValueError(f"Supabase delete error: {response.error}")
        except ValueError as e:
            # Supabase not configured or other config error
            print(f"[WARNING] [STORAGE] Storage not configured or error: {str(e)}")
            raise
        except Exception as e:
            import traceback
            print(f"[ERROR] [STORAGE] Failed to delete file {file_path}: {type(e).__name__}: {str(e)}")
            print(f"[ERROR] [STORAGE] Traceback: {traceback.format_exc()}")
            raise

