"""
S3 Storage Implementation

Handles file uploads and retrieval from Supabase Storage (S3-compatible).
All files are stored in tenant-scoped paths.
"""

import asyncio
from fastapi import UploadFile
from typing import Optional
from supabase import create_client, Client
import httpx

from config.settings import settings
from packages.core.storage.base import BaseStorage

# Initialize Supabase client (lazy)
_supabase_client: Optional[Client] = None

def get_supabase_client() -> Client:
    """Get or create Supabase client."""
    global _supabase_client
    if _supabase_client is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            raise ValueError("Supabase URL and Key must be configured")
        
        # Create Supabase client
        # Note: ClientOptions doesn't support httpx_client parameter in current Supabase version
        # If httpx compatibility issues arise, they should be handled at the httpx level
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    
    return _supabase_client


class S3Storage(BaseStorage):
    """
    Supabase Storage implementation (S3-compatible).
    
    File paths are tenant-scoped: {tenant_id}/{file_id}.{ext}
    """
    
    def __init__(self, tenant_id: str):
        super().__init__(tenant_id)
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
        supabase = get_supabase_client()

        # Workaround: storage3 download() can throw an internal UnboundLocalError
        # after transient HTTP/2 disconnects. Prefer downloading via signed URL
        # using httpx so errors are actionable and retryable.
        try:
            signed = supabase.storage.from_(self.bucket_name).create_signed_url(
                path=file_path,
                expires_in=3600,
            )
            signed_url = (
                signed.get("signedURL") if isinstance(signed, dict) else str(signed or "").strip()
            )
            if not signed_url:
                # Fallback for public buckets
                signed_url = supabase.storage.from_(self.bucket_name).get_public_url(file_path)
            if not signed_url:
                raise ValueError(f"Could not generate download URL for path: {file_path}")

            # Retry a couple times for transient disconnects.
            last_err: Optional[Exception] = None
            for attempt in range(1, 4):
                try:
                    timeout = httpx.Timeout(30.0, connect=10.0)
                    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                        resp = await client.get(signed_url)
                    if resp.status_code >= 400:
                        raise ValueError(
                            f"Storage download HTTP {resp.status_code}: {resp.text[:200]}"
                        )
                    if not resp.content:
                        raise ValueError(f"Downloaded file content is empty for path: {file_path}")
                    return resp.content
                except Exception as e:
                    last_err = e
                    if attempt < 3:
                        await asyncio.sleep(0.5 * attempt)
                        continue
                    raise
            raise last_err or ValueError("Unknown download failure")

        except ValueError:
            raise
        except Exception as e:
            import traceback
            error_msg = f"Failed to download file from storage: {str(e)}"
            print(f"[ERROR] [STORAGE] {error_msg}")
            print(f"[ERROR] [STORAGE] Traceback: {traceback.format_exc()}")
            raise ValueError(error_msg)
    
    async def delete_file(self, file_path: str):
        """Delete file from Supabase Storage."""
        try:
            supabase = get_supabase_client()
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


