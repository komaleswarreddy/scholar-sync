"""
Answer Cache

Caches answers for repeated queries to skip LLM calls.
"""

import hashlib
import json
import time
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock


class AnswerCache:
    """
    Cache layer for storing and retrieving answers to repeated queries.
    
    Features:
    - Query normalization (case-insensitive, whitespace handling)
    - Context-aware caching (considers active sources)
    - TTL-based expiration
    - Cache statistics
    """
    
    def __init__(
        self,
        cache_dir: Optional[str] = None,
        default_ttl_seconds: int = 3600,  # 1 hour
        max_cache_size: int = 1000
    ):
        """
        Initialize answer cache.
        
        Args:
            cache_dir: Directory to store cache (defaults to cache/answers/)
            default_ttl_seconds: Default time-to-live for cache entries
            max_cache_size: Maximum number of cache entries
        """
        self.cache_dir = Path(cache_dir or "cache/answers")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl_seconds
        self.max_cache_size = max_cache_size
        
        # In-memory cache: cache_key -> (answer, timestamp, sources_hash)
        self._cache: Dict[str, Dict[str, Any]] = {}
        
        # Thread safety
        self._lock = Lock()
        
        # Statistics
        self._hits = 0
        self._misses = 0
        
        # Load cache from disk on startup
        self._load_cache()
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for cache key generation."""
        # Lowercase, strip, remove extra whitespace
        normalized = " ".join(query.lower().strip().split())
        return normalized
    
    def _hash_query(
        self,
        query: str,
        source_ids: List[str],
        tenant_id: Optional[str] = None,
        cache_extra: str = "",
    ) -> str:
        """
        Create cache key from query and source IDs.
        
        Args:
            query: User query
            source_ids: List of active source IDs
            tenant_id: Tenant scope (avoids collisions if storage is ever shared)
            cache_extra: Optional suffix (e.g. NCERT global flags) so cache keys stay distinct.
            
        Returns:
            Cache key (hash)
        """
        normalized_query = self._normalize_query(query)
        
        # Include source IDs in hash (sorted for consistency)
        sources_str = ",".join(sorted(source_ids)) if source_ids else "none"
        tid = (tenant_id or "").strip().lower()
        extra = (cache_extra or "").strip()
        
        # Create hash
        cache_string = f"tenant::{tid}::{normalized_query}::sources::{sources_str}::extra::{extra}"
        cache_key = hashlib.sha256(cache_string.encode()).hexdigest()
        
        return cache_key
    
    def get(
        self,
        query: str,
        source_ids: List[str],
        tenant_id: Optional[str] = None,
        cache_extra: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached answer for query.
        
        Args:
            query: User query
            source_ids: List of active source IDs
            tenant_id: Optional tenant identifier
            
        Returns:
            Cached answer dict with 'answer', 'citations', 'timestamp', or None if not found
        """
        cache_key = self._hash_query(query, source_ids, tenant_id, cache_extra)
        
        with self._lock:
            if cache_key in self._cache:
                entry = self._cache[cache_key]
                
                # Check if expired
                if self._is_expired(entry):
                    del self._cache[cache_key]
                    self._misses += 1
                    return None
                
                # Return cached answer
                self._hits += 1
                return {
                    "answer": entry["answer"],
                    "citations": entry.get("citations", []),
                    "timestamp": entry["timestamp"],
                    "cached": True
                }
            
            self._misses += 1
            return None
    
    def set(
        self,
        query: str,
        source_ids: List[str],
        answer: str,
        citations: List[Dict[str, Any]],
        tenant_id: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
        cache_extra: str = "",
    ):
        """
        Cache answer for query.
        
        Args:
            query: User query
            source_ids: List of active source IDs
            answer: Generated answer
            citations: List of citations
            tenant_id: Optional tenant identifier
            ttl_seconds: Optional custom TTL (defaults to self.default_ttl)
        """
        cache_key = self._hash_query(query, source_ids, tenant_id, cache_extra)
        ttl = ttl_seconds or self.default_ttl
        expires_at = time.time() + ttl
        
        entry = {
            "answer": answer,
            "citations": citations,
            "timestamp": datetime.utcnow().isoformat(),
            "expires_at": expires_at,
            "query": self._normalize_query(query),
            "source_ids": sorted(source_ids) if source_ids else [],
            "tenant_id": tenant_id,
        }
        
        with self._lock:
            # Enforce max cache size (remove oldest if needed)
            if len(self._cache) >= self.max_cache_size:
                # Remove oldest entry (by expires_at)
                oldest_key = min(
                    self._cache.keys(),
                    key=lambda k: self._cache[k].get("expires_at", 0)
                )
                del self._cache[oldest_key]
            
            self._cache[cache_key] = entry
        
        # Persist to disk (async, non-blocking)
        self._save_cache_entry(cache_key, entry)
    
    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """Check if cache entry is expired."""
        expires_at = entry.get("expires_at", 0)
        return time.time() > expires_at
    
    def _load_cache(self):
        """Load cache from disk on startup."""
        cache_file = self.cache_dir / "cache.json"
        if not cache_file.exists():
            return
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            current_time = time.time()
            loaded_count = 0
            
            with self._lock:
                for cache_key, entry in data.items():
                    # Check if expired
                    expires_at = entry.get("expires_at", 0)
                    if current_time > expires_at:
                        continue
                    
                    self._cache[cache_key] = entry
                    loaded_count += 1
            
            if loaded_count > 0:
                print(f"[ANSWER_CACHE] Loaded {loaded_count} cache entries from disk")
        except Exception as e:
            print(f"[WARNING] Failed to load answer cache: {e}")
    
    def _save_cache_entry(self, cache_key: str, entry: Dict[str, Any]):
        """Save cache entry to disk (non-blocking)."""
        try:
            # Save individual entry to file (for persistence)
            # In production, consider using a proper cache backend (Redis, etc.)
            cache_file = self.cache_dir / "cache.json"
            
            # Load existing cache
            existing_cache = {}
            if cache_file.exists():
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        existing_cache = json.load(f)
                except:
                    existing_cache = {}
            
            # Update with new entry
            existing_cache[cache_key] = entry
            
            # Remove expired entries
            current_time = time.time()
            existing_cache = {
                k: v for k, v in existing_cache.items()
                if v.get("expires_at", 0) > current_time
            }
            
            # Save back
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(existing_cache, f, indent=2)
        except Exception as e:
            # Don't fail on cache save errors
            pass
    
    def clear(self, tenant_id: Optional[str] = None):
        """
        Clear cache entries.
        
        Args:
            tenant_id: Optional tenant filter (clear only for this tenant)
        """
        with self._lock:
            if tenant_id:
                # Clear only for specific tenant
                self._cache = {
                    k: v for k, v in self._cache.items()
                    if v.get("tenant_id") != tenant_id
                }
            else:
                # Clear all
                self._cache.clear()
        
        # Clear disk cache
        cache_file = self.cache_dir / "cache.json"
        if cache_file.exists() and not tenant_id:
            cache_file.unlink()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0.0
            
            # Count non-expired entries
            current_time = time.time()
            valid_entries = sum(
                1 for entry in self._cache.values()
                if entry.get("expires_at", 0) > current_time
            )
            
            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
                "cache_size": len(self._cache),
                "valid_entries": valid_entries,
                "max_size": self.max_cache_size,
            }
