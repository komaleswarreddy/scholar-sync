"""
Context Cache

Caches processed PDF content to avoid reprocessing the same files.
Uses file hash as cache key.
"""

import hashlib
import json
from typing import Optional, List, Tuple, Dict
from pathlib import Path
import os


class ContextCache:
    """
    Cache layer for processed PDFs.
    
    Stores:
    - Extracted and cleaned text
    - Chunks with metadata
    - Processing metadata (page counts, etc.)
    
    Uses file hash (SHA256) as cache key to detect identical files.
    """
    
    def __init__(self, cache_dir: str = "cache/processed_pdfs"):
        """
        Initialize context cache.
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_file_hash(self, file_content: bytes) -> str:
        """
        Generate SHA256 hash of file content.
        
        Args:
            file_content: PDF file bytes
            
        Returns:
            SHA256 hash as hex string
        """
        return hashlib.sha256(file_content).hexdigest()
    
    def get_cache_path(self, file_hash: str) -> Path:
        """Get cache file path for a hash."""
        return self.cache_dir / f"{file_hash}.json"
    
    def get_cached_content(
        self, 
        file_content: bytes,
        tenant_id: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Get cached processed content for a file.
        
        Args:
            file_content: PDF file bytes
            tenant_id: Optional tenant ID for metrics tracking
            
        Returns:
            Cached content dict with keys:
            - text: cleaned text
            - chunks: list of (chunk_text, chunk_metadata) tuples
            - metadata: processing metadata
            None if not cached
        """
        import time
        from packages.core.monitoring.metrics import get_metrics_collector
        
        start_time = time.time()
        file_hash = self.get_file_hash(file_content)
        cache_path = self.get_cache_path(file_hash)
        
        if not cache_path.exists():
            # Cache miss
            if tenant_id:
                latency_ms = (time.time() - start_time) * 1000
                metrics = get_metrics_collector()
                metrics.record_cache_operation(
                    tenant_id=tenant_id,
                    operation="miss",
                    cache_key=file_hash,
                    cache_type="context",
                    latency_ms=latency_ms
                )
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            
            # Cache hit - record metrics
            if tenant_id:
                import time
                from packages.core.monitoring.metrics import get_metrics_collector
                latency_ms = (time.time() - start_time) * 1000
                metrics = get_metrics_collector()
                metrics.record_cache_operation(
                    tenant_id=tenant_id,
                    operation="hit",
                    cache_key=file_hash,
                    cache_type="context",
                    latency_ms=latency_ms
                )
            
            # Convert chunks back to tuples
            chunks = [
                (chunk['text'], chunk['metadata'])
                for chunk in cached_data.get('chunks', [])
            ]
            
            return {
                'text': cached_data.get('text'),
                'chunks': chunks,
                'metadata': cached_data.get('metadata', {}),
                'file_hash': file_hash
            }
        except Exception as e:
            print(f"[WARNING] Failed to read cache for {file_hash}: {e}")
            return None
    
    def cache_content(
        self,
        file_content: bytes,
        text: str,
        chunks: List[Tuple[str, dict]],
        metadata: Optional[Dict] = None
    ):
        """
        Cache processed content.
        
        Args:
            file_content: Original PDF file bytes
            text: Cleaned extracted text
            chunks: List of (chunk_text, chunk_metadata) tuples
            metadata: Additional processing metadata
        """
        file_hash = self.get_file_hash(file_content)
        cache_path = self.get_cache_path(file_hash)
        
        try:
            # Convert chunks to JSON-serializable format
            chunks_data = [
                {
                    'text': chunk_text,
                    'metadata': chunk_metadata
                }
                for chunk_text, chunk_metadata in chunks
            ]
            
            cache_data = {
                'text': text,
                'chunks': chunks_data,
                'metadata': metadata or {},
                'file_hash': file_hash
            }
            
            # Write to cache file
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            print(f"[CACHE] Cached processed content for file hash: {file_hash[:16]}...")
        except Exception as e:
            print(f"[WARNING] Failed to cache content for {file_hash}: {e}")
    
    def clear_cache(self, file_hash: Optional[str] = None):
        """
        Clear cache entries.
        
        Args:
            file_hash: Specific file hash to clear, or None to clear all
        """
        if file_hash:
            cache_path = self.get_cache_path(file_hash)
            if cache_path.exists():
                cache_path.unlink()
                print(f"[CACHE] Cleared cache for {file_hash[:16]}...")
        else:
            # Clear all cache files
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            print(f"[CACHE] Cleared all cache files")
    
    def get_cache_size(self) -> int:
        """Get number of cached files."""
        return len(list(self.cache_dir.glob("*.json")))
