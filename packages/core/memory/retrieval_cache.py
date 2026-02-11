"""
Retrieval Cache

Caches query rewrites and reranked chunks for repeated questions.
Reduces redundant LLM calls for query rewriting and reranking.
"""

import hashlib
import json
import time
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock


class RetrievalCache:
    """
    Cache layer for query rewrites and reranked chunks.
    
    Caches:
    - query → rewritten_query
    - query → reranked_chunks
    """
    
    def __init__(
        self,
        cache_dir: Optional[str] = None,
        default_ttl_seconds: int = 3600,  # 1 hour
        max_cache_size: int = 500
    ):
        """
        Initialize retrieval cache.
        
        Args:
            cache_dir: Directory to store cache (defaults to cache/retrieval/)
            default_ttl_seconds: Default time-to-live for cache entries
            max_cache_size: Maximum number of cache entries
        """
        self.cache_dir = Path(cache_dir or "cache/retrieval")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl_seconds
        self.max_cache_size = max_cache_size
        
        # In-memory cache: cache_key -> (data, timestamp)
        self._rewrite_cache: Dict[str, Dict[str, Any]] = {}
        self._rerank_cache: Dict[str, Dict[str, Any]] = {}
        
        # Thread safety
        self._lock = Lock()
        
        # Statistics
        self._rewrite_hits = 0
        self._rewrite_misses = 0
        self._rerank_hits = 0
        self._rerank_misses = 0
        
        # Load cache from disk on startup
        self._load_cache()
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for cache key generation."""
        return " ".join(query.lower().strip().split())
    
    def _hash_query(self, query: str, source_ids: Optional[List[str]] = None) -> str:
        """
        Create cache key from query and source IDs.
        
        Args:
            query: User query
            source_ids: Optional list of active source IDs
            
        Returns:
            Cache key (hash)
        """
        normalized_query = self._normalize_query(query)
        
        # Include source IDs in hash (sorted for consistency)
        sources_str = ",".join(sorted(source_ids)) if source_ids else "none"
        
        # Create hash
        cache_string = f"{normalized_query}::sources::{sources_str}"
        cache_key = hashlib.sha256(cache_string.encode()).hexdigest()
        
        return cache_key
    
    def get_rewrite(
        self,
        query: str,
        source_ids: Optional[List[str]] = None
    ) -> Optional[List[str]]:
        """
        Get cached rewritten query.
        
        Args:
            query: User query
            source_ids: Optional list of active source IDs
            
        Returns:
            List of rewritten queries, or None if not cached
        """
        cache_key = self._hash_query(query, source_ids)
        
        with self._lock:
            if cache_key in self._rewrite_cache:
                entry = self._rewrite_cache[cache_key]
                
                # Check if expired
                if self._is_expired(entry):
                    del self._rewrite_cache[cache_key]
                    self._rewrite_misses += 1
                    return None
                
                # Return cached rewrite
                self._rewrite_hits += 1
                return entry.get("rewritten_queries", [])
            
            self._rewrite_misses += 1
            return None
    
    def set_rewrite(
        self,
        query: str,
        rewritten_queries: List[str],
        source_ids: Optional[List[str]] = None,
        ttl_seconds: Optional[int] = None
    ):
        """
        Cache rewritten query.
        
        Args:
            query: Original query
            rewritten_queries: List of rewritten query variants
            source_ids: Optional list of active source IDs
            ttl_seconds: Time-to-live in seconds (uses default if None)
        """
        cache_key = self._hash_query(query, source_ids)
        ttl = ttl_seconds or self.default_ttl
        
        with self._lock:
            # Evict oldest if cache is full
            if len(self._rewrite_cache) >= self.max_cache_size:
                self._evict_oldest(self._rewrite_cache)
            
            self._rewrite_cache[cache_key] = {
                "rewritten_queries": rewritten_queries,
                "timestamp": time.time(),
                "ttl": ttl,
                "query": query,
                "source_ids": source_ids or []
            }
            
            # Save to disk
            self._save_rewrite_cache(cache_key)
    
    def get_rerank(
        self,
        query: str,
        source_ids: Optional[List[str]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached reranked chunks.
        
        Args:
            query: User query
            source_ids: Optional list of active source IDs
            
        Returns:
            List of reranked chunk dicts, or None if not cached
        """
        cache_key = self._hash_query(query, source_ids)
        
        with self._lock:
            if cache_key in self._rerank_cache:
                entry = self._rerank_cache[cache_key]
                
                # Check if expired
                if self._is_expired(entry):
                    del self._rerank_cache[cache_key]
                    self._rerank_misses += 1
                    return None
                
                # Return cached reranked chunks
                self._rerank_hits += 1
                return entry.get("reranked_chunks", [])
            
            self._rerank_misses += 1
            return None
    
    def set_rerank(
        self,
        query: str,
        reranked_chunks: List[Dict[str, Any]],
        source_ids: Optional[List[str]] = None,
        ttl_seconds: Optional[int] = None
    ):
        """
        Cache reranked chunks.
        
        Args:
            query: User query
            reranked_chunks: List of reranked chunk dicts
            source_ids: Optional list of active source IDs
            ttl_seconds: Time-to-live in seconds (uses default if None)
        """
        cache_key = self._hash_query(query, source_ids)
        ttl = ttl_seconds or self.default_ttl
        
        with self._lock:
            # Evict oldest if cache is full
            if len(self._rerank_cache) >= self.max_cache_size:
                self._evict_oldest(self._rerank_cache)
            
            self._rerank_cache[cache_key] = {
                "reranked_chunks": reranked_chunks,
                "timestamp": time.time(),
                "ttl": ttl,
                "query": query,
                "source_ids": source_ids or []
            }
            
            # Save to disk
            self._save_rerank_cache(cache_key)
    
    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """Check if cache entry is expired."""
        timestamp = entry.get("timestamp", 0)
        ttl = entry.get("ttl", self.default_ttl)
        return time.time() - timestamp > ttl
    
    def _evict_oldest(self, cache: Dict[str, Any]):
        """Evict oldest entry from cache."""
        if not cache:
            return
        
        oldest_key = min(cache.keys(), key=lambda k: cache[k].get("timestamp", 0))
        del cache[oldest_key]
    
    def _save_rewrite_cache(self, cache_key: str):
        """Save rewrite cache entry to disk."""
        try:
            entry = self._rewrite_cache.get(cache_key)
            if entry:
                cache_file = self.cache_dir / f"rewrite_{cache_key}.json"
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(entry, f, indent=2, default=str)
        except Exception as e:
            print(f"[WARNING] Failed to save rewrite cache: {e}")
    
    def _save_rerank_cache(self, cache_key: str):
        """Save rerank cache entry to disk."""
        try:
            entry = self._rerank_cache.get(cache_key)
            if entry:
                cache_file = self.cache_dir / f"rerank_{cache_key}.json"
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(entry, f, indent=2, default=str)
        except Exception as e:
            print(f"[WARNING] Failed to save rerank cache: {e}")
    
    def _load_cache(self):
        """Load cache from disk on startup."""
        try:
            # Load rewrite cache
            for cache_file in self.cache_dir.glob("rewrite_*.json"):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        entry = json.load(f)
                        cache_key = cache_file.stem.replace("rewrite_", "")
                        if not self._is_expired(entry):
                            self._rewrite_cache[cache_key] = entry
                except Exception as e:
                    print(f"[WARNING] Failed to load rewrite cache file {cache_file}: {e}")
            
            # Load rerank cache
            for cache_file in self.cache_dir.glob("rerank_*.json"):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        entry = json.load(f)
                        cache_key = cache_file.stem.replace("rerank_", "")
                        if not self._is_expired(entry):
                            self._rerank_cache[cache_key] = entry
                except Exception as e:
                    print(f"[WARNING] Failed to load rerank cache file {cache_file}: {e}")
        except Exception as e:
            print(f"[WARNING] Failed to load retrieval cache: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "rewrite_hits": self._rewrite_hits,
            "rewrite_misses": self._rewrite_misses,
            "rerank_hits": self._rerank_hits,
            "rerank_misses": self._rerank_misses,
            "rewrite_cache_size": len(self._rewrite_cache),
            "rerank_cache_size": len(self._rerank_cache),
        }
