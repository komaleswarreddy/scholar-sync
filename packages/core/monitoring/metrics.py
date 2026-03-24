"""
Metrics Collector

Collects and aggregates metrics for LLM calls, cache operations, feature usage, etc.
Persists metrics to JSONL log files and loads them on startup.
"""

import json
import threading
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

# Singleton instance
_metrics_collector = None
_lock = threading.Lock()


class MetricsCollector:
    """
    Collects and aggregates metrics.
    
    Stores metrics in memory (deques) and persists to JSONL log files.
    Loads persisted metrics on startup.
    """
    
    def __init__(self):
        """Initialize metrics collector with in-memory storage."""
        self._lock = threading.Lock()
        
        # In-memory storage (deques with max size)
        self._llm_calls: deque = deque(maxlen=10000)
        self._cache_operations: deque = deque(maxlen=10000)
        self._feature_usage: deque = deque(maxlen=10000)
        self._document_costs: deque = deque(maxlen=10000)
        self._regenerate_attempts: deque = deque(maxlen=1000)
        
        # Log directory
        self._log_dir = Path("logs/metrics")
        self._log_dir.mkdir(parents=True, exist_ok=True)
        
        # Load persisted metrics on startup
        self._load_persisted_metrics()
    
    def _load_persisted_metrics(self):
        """Load metrics from JSONL log files."""
        try:
            # Load LLM calls
            llm_file = self._log_dir / "llm_calls.jsonl"
            if llm_file.exists():
                with open(llm_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines[-10000:]:  # Last 10k entries
                        try:
                            metric = json.loads(line.strip())
                            self._llm_calls.append(metric)
                        except:
                            continue
            
            # Load cache operations
            cache_file = self._log_dir / "cache_operations.jsonl"
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines[-10000:]:
                        try:
                            metric = json.loads(line.strip())
                            self._cache_operations.append(metric)
                        except:
                            continue
            
            # Load feature usage
            feature_file = self._log_dir / "feature_usage.jsonl"
            if feature_file.exists():
                with open(feature_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines[-10000:]:
                        try:
                            metric = json.loads(line.strip())
                            self._feature_usage.append(metric)
                        except:
                            continue
            
            # Load document costs
            doc_file = self._log_dir / "document_costs.jsonl"
            if doc_file.exists():
                with open(doc_file, 'r') as f:
                    for line in f:
                        try:
                            metric = json.loads(line.strip())
                            self._document_costs.append(metric)
                        except:
                            continue
            
        except Exception as e:
            pass
    
    def _write_metric(self, metric_type: str, metric: Dict[str, Any]):
        """Write metric to JSONL log file."""
        try:
            log_file = self._log_dir / f"{metric_type}.jsonl"
            with open(log_file, 'a') as f:
                f.write(json.dumps(metric) + '\n')
        except Exception:
            pass
    
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
        """Record an LLM API call."""
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
        
        self._write_metric("llm_calls", metric)
    
    def record_cache_operation(
        self,
        tenant_id: str,
        operation: str,  # "hit", "miss", "set", "delete"
        cache_key: Optional[str] = None,
        cache_type: Optional[str] = None,
        latency_ms: Optional[float] = None,
        user_id: Optional[str] = None,
    ):
        """Record a cache operation."""
        metric = {
            "timestamp": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id,
            "user_id": user_id,
            "operation": operation,
            "cache_key": cache_key,
            "cache_type": cache_type,
            "latency_ms": latency_ms,
        }
        
        with self._lock:
            self._cache_operations.append(metric)
        
        self._write_metric("cache_operations", metric)
    
    def record_feature_usage(
        self,
        tenant_id: str,
        feature: str,
        user_id: Optional[str] = None,
        endpoint: Optional[str] = None,
    ):
        """Record feature usage."""
        metric = {
            "timestamp": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id,
            "user_id": user_id,
            "feature": feature,
            "endpoint": endpoint,
        }
        
        with self._lock:
            self._feature_usage.append(metric)
        
        self._write_metric("feature_usage", metric)
    
    def record_document_cost(
        self,
        tenant_id: str,
        document_id: str,
        cost: float,
        user_id: Optional[str] = None,
    ):
        """Record document processing cost."""
        metric = {
            "timestamp": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id,
            "user_id": user_id,
            "document_id": document_id,
            "cost": cost,
        }
        
        with self._lock:
            self._document_costs.append(metric)
        
        self._write_metric("document_costs", metric)
    
    def get_metrics_summary(
        self,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get aggregated metrics summary."""
        with self._lock:
            # Filter LLM calls
            llm_calls = list(self._llm_calls)
            if tenant_id:
                llm_calls = [m for m in llm_calls if str(m.get("tenant_id")) == str(tenant_id)]
            if user_id:
                llm_calls = [m for m in llm_calls if str(m.get("user_id")) == str(user_id)]
            
            # Calculate LLM metrics
            total_tokens = sum(m.get("total_tokens", 0) for m in llm_calls)
            input_tokens = sum(m.get("prompt_tokens", 0) for m in llm_calls)
            output_tokens = sum(m.get("completion_tokens", 0) for m in llm_calls)
            total_cost = sum(m.get("cost", 0) for m in llm_calls)
            total_calls = len(llm_calls)
            
            # Calculate latency
            latencies = [m.get("latency_ms", 0) for m in llm_calls if m.get("latency_ms") is not None]
            avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
            
            # Calculate percentiles
            p50_latency = 0.0
            p95_latency = 0.0
            p99_latency = 0.0
            min_latency = min(latencies) if latencies else 0.0
            max_latency = max(latencies) if latencies else 0.0
            
            if len(latencies) > 0:
                sorted_latencies = sorted(latencies)
                n = len(sorted_latencies)
                p50_latency = sorted_latencies[int(n * 0.50)] if n > 0 else 0.0
                p95_latency = sorted_latencies[int(n * 0.95)] if n > 0 else 0.0
                p99_latency = sorted_latencies[int(n * 0.99)] if n > 0 else 0.0
            
            # Filter cache operations
            cache_ops = list(self._cache_operations)
            if tenant_id:
                cache_ops = [m for m in cache_ops if str(m.get("tenant_id")) == str(tenant_id)]
            if user_id:
                # Only include cache operations that match the specific user_id
                # Exclude operations with no user_id when filtering for a specific user
                cache_ops = [m for m in cache_ops if m.get("user_id") and str(m.get("user_id")) == str(user_id)]
            
            # Calculate cache metrics
            cache_hits = sum(1 for m in cache_ops if m.get("operation") == "hit")
            cache_misses = sum(1 for m in cache_ops if m.get("operation") == "miss")
            cache_total = cache_hits + cache_misses
            # Return None if no cache operations (so frontend can show "—" or "No data")
            cache_hit_rate = cache_hits / cache_total if cache_total > 0 else None
            
            # Filter feature usage
            feature_usage_list = list(self._feature_usage)
            if tenant_id:
                feature_usage_list = [m for m in feature_usage_list if str(m.get("tenant_id")) == str(tenant_id)]
            if user_id:
                # Only include feature usage that matches the specific user_id
                # Exclude operations with no user_id when filtering for a specific user
                feature_usage_list = [m for m in feature_usage_list if m.get("user_id") and str(m.get("user_id")) == str(user_id)]
            
            # Calculate feature usage counts
            feature_counts = {}
            for m in feature_usage_list:
                feature = m.get("feature", "unknown")
                feature_counts[feature] = feature_counts.get(feature, 0) + 1
            
            # Filter document costs
            doc_costs = list(self._document_costs)
            if tenant_id:
                doc_costs = [m for m in doc_costs if str(m.get("tenant_id")) == str(tenant_id)]
            if user_id:
                # Only include document costs that match the specific user_id
                # Exclude operations with no user_id when filtering for a specific user
                doc_costs = [m for m in doc_costs if m.get("user_id") and str(m.get("user_id")) == str(user_id)]
            
            total_doc_cost = sum(m.get("cost", 0) for m in doc_costs)
            
            return {
                "tokens": {
                    "total": total_tokens,
                    "input": input_tokens,
                    "output": output_tokens,
                },
                "costs": {
                    "total": total_cost,
                    "avg_per_call": total_cost / total_calls if total_calls > 0 else 0.0,
                },
                "llm_calls": {
                    "total": total_calls,
                    "avg_tokens_per_call": total_tokens / total_calls if total_calls > 0 else 0.0,
                },
                "latency": {
                    "average": avg_latency,
                    "min": min_latency,
                    "max": max_latency,
                    "p50": p50_latency,
                    "p95": p95_latency,
                    "p99": p99_latency,
                    "total_calls_with_latency": len(latencies),
                },
                "cache": {
                    "hits": cache_hits,
                    "misses": cache_misses,
                    "hit_rate": cache_hit_rate,
                },
                "feature_usage": feature_counts,
                "document_costs": {
                    "total_cost": total_doc_cost,
                    "count": len(doc_costs),
                },
            }
    
    def get_cache_hit_rate(
        self,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> float:
        """Get cache hit rate."""
        with self._lock:
            cache_ops = list(self._cache_operations)
            if tenant_id:
                cache_ops = [m for m in cache_ops if str(m.get("tenant_id")) == str(tenant_id)]
            if user_id:
                # Only include cache operations that match the specific user_id
                # Exclude operations with no user_id when filtering for a specific user
                cache_ops = [m for m in cache_ops if m.get("user_id") and str(m.get("user_id")) == str(user_id)]
            
            hits = sum(1 for m in cache_ops if m.get("operation") == "hit")
            misses = sum(1 for m in cache_ops if m.get("operation") == "miss")
            total = hits + misses
            
            # Return None if no cache operations (so frontend can show "—" or "No data")
            return hits / total if total > 0 else None
    
    def reload_metrics_from_logs(self):
        """Reload metrics from log files."""
        with self._lock:
            self._llm_calls.clear()
            self._cache_operations.clear()
            self._feature_usage.clear()
            self._document_costs.clear()
            self._regenerate_attempts.clear()
        
        self._load_persisted_metrics()


def get_metrics_collector() -> MetricsCollector:
    """Get singleton metrics collector instance."""
    global _metrics_collector
    
    if _metrics_collector is None:
        with _lock:
            if _metrics_collector is None:
                _metrics_collector = MetricsCollector()
    
    return _metrics_collector
