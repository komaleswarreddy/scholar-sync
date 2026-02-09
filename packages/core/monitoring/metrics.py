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
        
        # Load persisted metrics from log files on startup
        self._load_persisted_metrics()
    
    def _load_schema(self):
        """Load metrics schema from config."""
        schema_path = Path("config/metrics_schema.json")
        if schema_path.exists():
            with open(schema_path, 'r') as f:
                self.schema = json.load(f)
        else:
            self.schema = {}
    
    def _load_persisted_metrics(self):
        """Load metrics from log files on startup to persist across restarts."""
        try:
            # Load LLM calls (last 10k from log file)
            llm_calls_file = self.storage_path / "llm_calls.jsonl"
            if llm_calls_file.exists():
                loaded_count = 0
                try:
                    with open(llm_calls_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        # Load last 10000 lines (most recent)
                        for line in lines[-10000:]:
                            if not line.strip():
                                continue
                            try:
                                metric = json.loads(line.strip())
                                # Validate metric has required fields
                                if "tenant_id" in metric and "total_tokens" in metric:
                                    self._llm_calls.append(metric)
                                    loaded_count += 1
                            except (json.JSONDecodeError, KeyError) as e:
                                # Skip malformed lines
                                continue
                    if loaded_count > 0:
                        print(f"[METRICS] Loaded {loaded_count} LLM call metrics from log file")
                except Exception as e:
                    print(f"[WARNING] Failed to load LLM calls from {llm_calls_file}: {e}")
            
            # Load cache operations
            cache_ops_file = self.storage_path / "cache_operations.jsonl"
            if cache_ops_file.exists():
                loaded_count = 0
                with open(cache_ops_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines[-10000:]:
                        try:
                            metric = json.loads(line.strip())
                            self._cache_operations.append(metric)
                            # Update aggregated stats
                            if metric.get("operation") in ["hit", "miss"]:
                                tenant_id = metric.get("tenant_id", "all")
                                cache_type = metric.get("cache_type", "default")
                                key = f"{tenant_id}:{cache_type}"
                                stat_key = "hits" if metric["operation"] == "hit" else "misses"
                                self._cache_stats[key][stat_key] += 1
                            loaded_count += 1
                        except json.JSONDecodeError:
                            continue
                if loaded_count > 0:
                    print(f"[METRICS] Loaded {loaded_count} cache operation metrics from log file")
            
            # Load document costs
            doc_costs_file = self.storage_path / "document_costs.jsonl"
            if doc_costs_file.exists():
                loaded_count = 0
                with open(doc_costs_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            metric = json.loads(line.strip())
                            source_id = metric.get("source_id")
                            if source_id:
                                self._document_costs[source_id] = metric
                                loaded_count += 1
                        except json.JSONDecodeError:
                            continue
                if loaded_count > 0:
                    print(f"[METRICS] Loaded {loaded_count} document cost metrics from log file")
            
            # Load feature usage
            feature_usage_file = self.storage_path / "feature_usage.jsonl"
            if feature_usage_file.exists():
                loaded_count = 0
                with open(feature_usage_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines[-10000:]:
                        try:
                            metric = json.loads(line.strip())
                            self._feature_usage.append(metric)
                            feature = metric.get("feature")
                            if feature:
                                self._feature_counts[feature] += 1
                            loaded_count += 1
                        except json.JSONDecodeError:
                            continue
                if loaded_count > 0:
                    print(f"[METRICS] Loaded {loaded_count} feature usage metrics from log file")
            
            # Load regenerate attempts
            regenerate_file = self.storage_path / "regenerate_attempts.jsonl"
            if regenerate_file.exists():
                loaded_count = 0
                with open(regenerate_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines[-1000:]:
                        try:
                            metric = json.loads(line.strip())
                            self._regenerate_attempts.append(metric)
                            user_id = metric.get("user_id")
                            if user_id:
                                self._regenerate_counts[user_id] += 1
                            loaded_count += 1
                        except json.JSONDecodeError:
                            continue
                if loaded_count > 0:
                    print(f"[METRICS] Loaded {loaded_count} regenerate attempt metrics from log file")
            
            total_loaded = len(self._llm_calls) + len(self._cache_operations) + len(self._feature_usage)
            if total_loaded > 0:
                print(f"[METRICS] Metrics persistence: Loaded {total_loaded} total metrics from log files")
                print(f"[METRICS] Breakdown: LLM calls: {len(self._llm_calls)}, Cache ops: {len(self._cache_operations)}, Features: {len(self._feature_usage)}, Documents: {len(self._document_costs)}")
            else:
                print(f"[METRICS] No persisted metrics found in log files (this is normal for first run)")
        except Exception as e:
            import traceback
            print(f"[WARNING] Failed to load persisted metrics: {e}")
            print(f"[WARNING] Traceback: {traceback.format_exc()}")
            # Continue without persisted metrics (fresh start)
    
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
            # Debug logging
            print(f"[METRICS] Recorded LLM call: tenant={tenant_id}, model={model}, tokens={total_tokens}, cost={cost:.6f}, feature={feature_tag}")
            print(f"[METRICS] Total LLM calls in memory: {len(self._llm_calls)}")
        
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
        
        Includes both in-memory metrics and metrics loaded from log files.
        
        Args:
            tenant_id: Optional tenant filter
            
        Returns:
            Dictionary with aggregated metrics
        """
        with self._lock:
            # Debug: Log total calls before filtering
            print(f"[METRICS] get_metrics_summary called: tenant_id={tenant_id}, total_calls_in_memory={len(self._llm_calls)}")
            
            # Filter by tenant if provided
            llm_calls = [m for m in self._llm_calls if not tenant_id or m.get("tenant_id") == tenant_id]
            cache_ops = [m for m in self._cache_operations if not tenant_id or m.get("tenant_id") == tenant_id]
            
            print(f"[METRICS] After filtering: tenant_id={tenant_id}, filtered_calls={len(llm_calls)}")
            
            # Calculate totals
            total_tokens = sum(m.get("total_tokens", 0) for m in llm_calls)
            total_cost = sum(m.get("cost", 0.0) for m in llm_calls)
            total_calls = len(llm_calls)
            
            print(f"[METRICS] Calculated totals: calls={total_calls}, tokens={total_tokens}, cost={total_cost:.6f}")
            
            # Debug: Log what we're returning
            if total_calls > 0:
                print(f"[METRICS] Returning summary: {total_calls} calls, {total_tokens} tokens, ${total_cost:.6f} cost")
            else:
                print(f"[METRICS] WARNING: No metrics found for tenant_id={tenant_id}")
                print(f"[METRICS] Total metrics in memory (all tenants): LLM calls={len(self._llm_calls)}, Cache ops={len(self._cache_operations)}")
                # Check if log files exist
                llm_calls_file = self.storage_path / "llm_calls.jsonl"
                if llm_calls_file.exists():
                    file_size = llm_calls_file.stat().st_size
                    print(f"[METRICS] Log file exists: {llm_calls_file} ({file_size} bytes)")
                else:
                    print(f"[METRICS] Log file does not exist: {llm_calls_file}")
            
            
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
            
            # Calculate token breakdown
            input_tokens = sum(m.get("prompt_tokens", 0) for m in llm_calls)
            output_tokens = sum(m.get("completion_tokens", 0) for m in llm_calls)
            
            return {
                "llm_calls": {
                    "total": total_calls,
                    "total_tokens": total_tokens,
                    "total_cost": total_cost,
                    "avg_tokens_per_call": total_tokens / total_calls if total_calls > 0 else 0,
                    "avg_cost_per_call": total_cost / total_calls if total_calls > 0 else 0,
                },
                "tokens": {
                    "input": input_tokens,
                    "output": output_tokens,
                    "total": total_tokens,
                },
                "costs": {
                    "total": total_cost,
                    "avg_per_call": total_cost / total_calls if total_calls > 0 else 0.0,
                },
                "cache": {
                    "hits": cache_hits,
                    "misses": cache_misses,
                    "hit_rate": cache_hit_rate,
                },
                "feature_usage": feature_counts,
                "regenerate_attempts": regenerate_count,
                "document_costs": {
                    "total_documents": len([d for d in self._document_costs.values() if not tenant_id or d.get("tenant_id") == tenant_id]),
                    "total_cost": sum(d.get("total_cost", 0) for d in self._document_costs.values() if not tenant_id or d.get("tenant_id") == tenant_id),
                },
            }
    
    def reload_metrics_from_logs(self):
        """
        Reload metrics from log files.
        
        Useful for refreshing metrics after they've been written to disk.
        """
        print("[METRICS] Reloading metrics from log files...")
        # Clear current in-memory metrics
        with self._lock:
            self._llm_calls.clear()
            self._cache_operations.clear()
            self._document_costs.clear()
            self._feature_usage.clear()
            self._regenerate_attempts.clear()
            self._cache_stats.clear()
            self._feature_counts.clear()
            self._regenerate_counts.clear()
        
        # Reload from files
        self._load_persisted_metrics()
        print("[METRICS] Metrics reloaded from log files")


# Global singleton instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
