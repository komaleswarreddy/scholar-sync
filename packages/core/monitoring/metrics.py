"""
Metrics Collection

Comprehensive metrics collection for PHASE 0 - Baseline & Observability.
Tracks tokens, costs, cache operations, feature usage, and more.
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
from collections import defaultdict, deque
import asyncio
from threading import Lock

from config.settings import settings


class MetricsCollector:
    """
    Collects and stores application metrics.
    
    Tracks:
    - LLM call tokens and costs
    - Cache hit/miss rates
    - Document-level costs
    - Feature usage
    - Regenerate attempts
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize metrics collector.
        
        Args:
            storage_path: Optional path to store metrics logs (defaults to logs/metrics/)
        """
        self.storage_path = Path(storage_path or "logs/metrics")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory storage for real-time metrics
        self._llm_calls: deque = deque(maxlen=10000)  # Last 10k calls
        self._cache_operations: deque = deque(maxlen=10000)
        self._document_costs: Dict[str, Dict] = {}  # source_id -> cost data
        self._feature_usage: deque = deque(maxlen=10000)
        self._regenerate_attempts: deque = deque(maxlen=1000)
        
        # Aggregated counters
        self._cache_stats = defaultdict(lambda: {"hits": 0, "misses": 0})
        self._feature_counts = defaultdict(int)
        self._regenerate_counts = defaultdict(int)  # user_id -> count
        
        # Thread safety
        self._lock = Lock()
        
        # Load metrics schema
        self._load_schema()
    
    def _load_schema(self):
        """Load metrics schema from config."""
        schema_path = Path("config/metrics_schema.json")
        if schema_path.exists():
            with open(schema_path, 'r') as f:
                self.schema = json.load(f)
        else:
            self.schema = {}
    
    def record_llm_call(
        self,
        tenant_id: str,
        user_id: str,
        model: str,
        provider: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        cost: float,
        feature_tag: Optional[str] = None,
        request_id: Optional[str] = None,
        latency_ms: Optional[float] = None,
    ):
        """
        Record an LLM API call with token usage and cost.
        
        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            model: Model name (e.g., "gpt-4o-mini")
            provider: Provider name (e.g., "openai", "gemini")
            prompt_tokens: Input tokens
            completion_tokens: Output tokens
            total_tokens: Total tokens
            cost: Calculated cost in USD
            feature_tag: Optional feature identifier (e.g., "chat", "studio")
            request_id: Optional request identifier for tracing
            latency_ms: Optional request latency in milliseconds
        """
        metric = {
            "timestamp": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id,
            "user_id": user_id,
            "model": model,
            "provider": provider,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost": cost,
            "feature_tag": feature_tag,
            "request_id": request_id,
            "latency_ms": latency_ms,
        }
        
        with self._lock:
            self._llm_calls.append(metric)
        
        # Write to log file
        self._write_log("llm_calls", metric)
    
    def record_cache_operation(
        self,
        tenant_id: str,
        operation: str,  # "hit", "miss", "set", "delete"
        cache_key: Optional[str] = None,
        cache_type: Optional[str] = None,
        latency_ms: Optional[float] = None,
    ):
        """
        Record a cache operation.
        
        Args:
            tenant_id: Tenant identifier
            operation: Operation type ("hit", "miss", "set", "delete")
            cache_key: Optional cache key
            cache_type: Optional cache type ("context", "embedding", "response")
            latency_ms: Optional operation latency
        """
        metric = {
            "timestamp": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id,
            "operation": operation,
            "cache_key": cache_key,
            "cache_type": cache_type,
            "latency_ms": latency_ms,
        }
        
        with self._lock:
            self._cache_operations.append(metric)
            
            # Update aggregated stats
            if operation in ["hit", "miss"]:
                key = f"{tenant_id}:{cache_type or 'default'}"
                # Map operation to correct plural form
                stat_key = "hits" if operation == "hit" else "misses"
                self._cache_stats[key][stat_key] += 1
        
        self._write_log("cache_operations", metric)
    
    def record_document_cost(
        self,
        tenant_id: str,
        source_id: str,
        total_cost: float,
        processing_cost: Optional[float] = None,
        embedding_cost: Optional[float] = None,
        chunks_count: Optional[int] = None,
        pages_count: Optional[int] = None,
    ):
        """
        Record cost for a document/source.
        
        Args:
            tenant_id: Tenant identifier
            source_id: Source/document identifier
            total_cost: Total cost in USD
            processing_cost: Optional processing cost
            embedding_cost: Optional embedding generation cost
            chunks_count: Optional number of chunks
            pages_count: Optional number of pages
        """
        metric = {
            "timestamp": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id,
            "source_id": source_id,
            "total_cost": total_cost,
            "processing_cost": processing_cost,
            "embedding_cost": embedding_cost,
            "chunks_count": chunks_count,
            "pages_count": pages_count,
        }
        
        with self._lock:
            self._document_costs[source_id] = metric
        
        self._write_log("document_costs", metric)
    
    def record_feature_usage(
        self,
        tenant_id: str,
        user_id: str,
        feature: str,  # "chat", "upload", "regenerate", "studio", "search", "export"
        endpoint: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        """
        Record feature-level usage.
        
        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            feature: Feature name
            endpoint: Optional API endpoint
            request_id: Optional request identifier
        """
        metric = {
            "timestamp": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id,
            "user_id": user_id,
            "feature": feature,
            "endpoint": endpoint,
            "request_id": request_id,
        }
        
        with self._lock:
            self._feature_usage.append(metric)
            self._feature_counts[feature] += 1
        
        self._write_log("feature_usage", metric)
    
    def record_regenerate_attempt(
        self,
        tenant_id: str,
        user_id: str,
        chat_id: Optional[str] = None,
        message_id: Optional[str] = None,
        attempt_number: Optional[int] = None,
    ):
        """
        Record a regenerate button attempt.
        
        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            chat_id: Optional chat identifier
            message_id: Optional message identifier
            attempt_number: Optional attempt number
        """
        metric = {
            "timestamp": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id,
            "user_id": user_id,
            "chat_id": chat_id,
            "message_id": message_id,
            "attempt_number": attempt_number,
        }
        
        with self._lock:
            self._regenerate_attempts.append(metric)
            self._regenerate_counts[user_id] += 1
        
        self._write_log("regenerate_attempts", metric)
    
    def _write_log(self, log_type: str, metric: Dict[str, Any]):
        """Write metric to log file."""
        try:
            log_file = self.storage_path / f"{log_type}.jsonl"
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(metric) + '\n')
        except Exception as e:
            # Don't fail on log write errors
            print(f"[WARNING] Failed to write metric log: {e}")
    
    def get_cache_hit_rate(self, tenant_id: Optional[str] = None, cache_type: Optional[str] = None) -> float:
        """
        Get cache hit rate.
        
        Args:
            tenant_id: Optional tenant filter
            cache_type: Optional cache type filter
            
        Returns:
            Hit rate as float (0.0 to 1.0)
        """
        with self._lock:
            key = f"{tenant_id or 'all'}:{cache_type or 'default'}"
            stats = self._cache_stats.get(key, {"hits": 0, "misses": 0})
            total = stats["hits"] + stats["misses"]
            if total == 0:
                return 0.0
            return stats["hits"] / total
    
    def get_metrics_summary(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get aggregated metrics summary.
        
        Args:
            tenant_id: Optional tenant filter
            
        Returns:
            Dictionary with aggregated metrics
        """
        with self._lock:
            # Filter by tenant if provided
            llm_calls = [m for m in self._llm_calls if not tenant_id or m["tenant_id"] == tenant_id]
            cache_ops = [m for m in self._cache_operations if not tenant_id or m["tenant_id"] == tenant_id]
            
            # Calculate totals
            total_tokens = sum(m["total_tokens"] for m in llm_calls)
            total_cost = sum(m["cost"] for m in llm_calls)
            total_calls = len(llm_calls)
            
            # Cache stats
            cache_hits = sum(1 for m in cache_ops if m["operation"] == "hit")
            cache_misses = sum(1 for m in cache_ops if m["operation"] == "miss")
            cache_total = cache_hits + cache_misses
            cache_hit_rate = cache_hits / cache_total if cache_total > 0 else 0.0
            
            # Feature usage
            feature_counts = {}
            for metric in self._feature_usage:
                if not tenant_id or metric["tenant_id"] == tenant_id:
                    feature = metric["feature"]
                    feature_counts[feature] = feature_counts.get(feature, 0) + 1
            
            # Regenerate attempts
            regenerate_count = sum(
                1 for m in self._regenerate_attempts
                if not tenant_id or m["tenant_id"] == tenant_id
            )
            
            return {
                "llm_calls": {
                    "total": total_calls,
                    "total_tokens": total_tokens,
                    "total_cost": total_cost,
                    "avg_tokens_per_call": total_tokens / total_calls if total_calls > 0 else 0,
                    "avg_cost_per_call": total_cost / total_calls if total_calls > 0 else 0,
                },
                "cache": {
                    "hits": cache_hits,
                    "misses": cache_misses,
                    "hit_rate": cache_hit_rate,
                },
                "feature_usage": feature_counts,
                "regenerate_attempts": regenerate_count,
                "document_costs": {
                    "total_documents": len([d for d in self._document_costs.values() if not tenant_id or d["tenant_id"] == tenant_id]),
                    "total_cost": sum(d["total_cost"] for d in self._document_costs.values() if not tenant_id or d["tenant_id"] == tenant_id),
                },
            }


# Global singleton instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
