"""
Alert Manager

Manages alerts for hallucination rate, cache miss anomalies, token spikes, and cost spikes.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from collections import deque
from pathlib import Path

from packages.core.monitoring.metrics import get_metrics_collector


class AlertManager:
    """
    Manages alerts based on metrics thresholds.
    
    Alert Types:
    - hallucination_rate: When negative feedback rate exceeds threshold
    - cache_miss_anomaly: When cache miss rate increases significantly
    - token_spike: When token usage spikes abnormally
    - cost_spike: When cost spikes abnormally
    """
    
    def __init__(self):
        """Initialize alert manager."""
        self.metrics = get_metrics_collector()
        self.alerts_log: deque = deque(maxlen=1000)  # Last 1000 alerts
        
        # Load alert thresholds from schema
        self._load_alert_config()
    
    def _load_alert_config(self):
        """Load alert configuration from metrics schema."""
        schema_path = Path("config/metrics_schema.json")
        if schema_path.exists():
            with open(schema_path, 'r') as f:
                schema = json.load(f)
                self.alert_config = schema.get("alerts", {})
        else:
            # Default thresholds
            self.alert_config = {
                "hallucination_rate": {
                    "threshold": 0.15,
                    "window_minutes": 60,
                    "severity": "high"
                },
                "cache_miss_anomaly": {
                    "threshold": 0.3,
                    "window_minutes": 30,
                    "severity": "medium"
                },
                "token_spike": {
                    "threshold_multiplier": 3.0,
                    "window_minutes": 15,
                    "severity": "high"
                },
                "cost_spike": {
                    "threshold_multiplier": 3.0,
                    "window_minutes": 15,
                    "severity": "critical"
                }
            }
    
    def check_hallucination_rate(
        self,
        tenant_id: Optional[str] = None,
        window_minutes: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Check if hallucination rate exceeds threshold.
        
        Hallucination is measured by negative feedback rate (thumbs_down).
        This is a placeholder - actual implementation would query message feedback.
        
        Args:
            tenant_id: Optional tenant filter
            window_minutes: Optional time window (defaults to config)
            
        Returns:
            Alert dict if threshold exceeded, None otherwise
        """
        # TODO: Implement actual hallucination rate calculation from message feedback
        # For now, return None (no alert)
        return None
    
    def check_cache_miss_anomaly(
        self,
        tenant_id: Optional[str] = None,
        window_minutes: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Check if cache miss rate has increased significantly.
        
        Args:
            tenant_id: Optional tenant filter
            window_minutes: Optional time window (defaults to config)
            
        Returns:
            Alert dict if anomaly detected, None otherwise
        """
        config = self.alert_config.get("cache_miss_anomaly", {})
        threshold = config.get("threshold", 0.3)
        window = window_minutes or config.get("window_minutes", 30)
        
        # Get cache hit rate
        hit_rate = self.metrics.get_cache_hit_rate(tenant_id=tenant_id)
        miss_rate = 1.0 - hit_rate
        
        if miss_rate > threshold:
            alert = {
                "timestamp": datetime.utcnow().isoformat(),
                "alert_type": "cache_miss_anomaly",
                "severity": config.get("severity", "medium"),
                "tenant_id": tenant_id,
                "message": f"Cache miss rate ({miss_rate:.2%}) exceeds threshold ({threshold:.2%})",
                "threshold": threshold,
                "actual_value": miss_rate,
            }
            self._record_alert(alert)
            return alert
        
        return None
    
    def check_token_spike(
        self,
        tenant_id: Optional[str] = None,
        window_minutes: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Check if token usage has spiked abnormally.
        
        Args:
            tenant_id: Optional tenant filter
            window_minutes: Optional time window (defaults to config)
            
        Returns:
            Alert dict if spike detected, None otherwise
        """
        config = self.alert_config.get("token_spike", {})
        multiplier = config.get("threshold_multiplier", 3.0)
        window = window_minutes or config.get("window_minutes", 15)
        
        # Calculate average tokens in baseline window (previous period)
        # and compare to current window
        # This is simplified - in production, would use time-series analysis
        
        summary = self.metrics.get_metrics_summary(tenant_id=tenant_id)
        avg_tokens = summary.get("llm_calls", {}).get("avg_tokens_per_call", 0)
        
        # Simple heuristic: if average is very high, might be a spike
        # In production, would compare to historical baseline
        if avg_tokens > 10000:  # Arbitrary high threshold
            alert = {
                "timestamp": datetime.utcnow().isoformat(),
                "alert_type": "token_spike",
                "severity": config.get("severity", "high"),
                "tenant_id": tenant_id,
                "message": f"Token usage spike detected: avg {avg_tokens:.0f} tokens per call",
                "actual_value": avg_tokens,
            }
            self._record_alert(alert)
            return alert
        
        return None
    
    def check_cost_spike(
        self,
        tenant_id: Optional[str] = None,
        window_minutes: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Check if cost has spiked abnormally.
        
        Args:
            tenant_id: Optional tenant filter
            window_minutes: Optional time window (defaults to config)
            
        Returns:
            Alert dict if spike detected, None otherwise
        """
        config = self.alert_config.get("cost_spike", {})
        multiplier = config.get("threshold_multiplier", 3.0)
        window = window_minutes or config.get("window_minutes", 15)
        
        summary = self.metrics.get_metrics_summary(tenant_id=tenant_id)
        total_cost = summary.get("llm_calls", {}).get("total_cost", 0)
        avg_cost = summary.get("llm_calls", {}).get("avg_cost_per_call", 0)
        
        # Simple heuristic: if average cost per call is very high
        if avg_cost > 0.10:  # $0.10 per call is high
            alert = {
                "timestamp": datetime.utcnow().isoformat(),
                "alert_type": "cost_spike",
                "severity": config.get("severity", "critical"),
                "tenant_id": tenant_id,
                "message": f"Cost spike detected: ${avg_cost:.4f} per call, total ${total_cost:.2f}",
                "actual_value": avg_cost,
            }
            self._record_alert(alert)
            return alert
        
        return None
    
    def _record_alert(self, alert: Dict[str, Any]):
        """Record alert to log and in-memory storage."""
        self.alerts_log.append(alert)
        
        # Write to log file
        try:
            log_file = Path("logs/metrics/alerts.jsonl")
            log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(alert) + '\n')
        except Exception as e:
            print(f"[WARNING] Failed to write alert log: {e}")
    
    def get_recent_alerts(
        self,
        alert_type: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recent alerts.
        
        Args:
            alert_type: Optional filter by alert type
            severity: Optional filter by severity
            limit: Maximum number of alerts to return
            
        Returns:
            List of alert dicts
        """
        alerts = list(self.alerts_log)
        
        if alert_type:
            alerts = [a for a in alerts if a.get("alert_type") == alert_type]
        
        if severity:
            alerts = [a for a in alerts if a.get("severity") == severity]
        
        return alerts[-limit:]
    
    def reset_all_alerts(self):
        """
        Reset all alerts by clearing in-memory storage and deleting log file.
        
        This will permanently delete all alerts data. Use with caution.
        """
        print("[ALERTS] Resetting all alerts...")
        
        # Clear in-memory alerts
        self.alerts_log.clear()
        
        # Delete alert log file
        log_file = Path("logs/metrics/alerts.jsonl")
        deleted = False
        try:
            if log_file.exists():
                log_file.unlink()
                deleted = True
                print(f"[ALERTS] Deleted alerts.jsonl")
        except Exception as e:
            print(f"[WARNING] Failed to delete alerts.jsonl: {e}")
        
        print(f"[ALERTS] Reset complete. Alerts cleared.")
        return {
            "status": "success",
            "deleted_file": deleted,
            "message": "All alerts have been reset"
        }


# Global singleton instance
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get or create global alert manager instance."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager
