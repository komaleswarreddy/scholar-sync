"""
Cost Manager

🔒 SINGLE SOURCE OF TRUTH for cost operations.

Tracks and manages LLM API costs, enforces budgets, and records usage.
Implements pricing configuration from models.yaml.
"""

import yaml
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from packages.core.monitoring.metrics import get_metrics_collector


class CostManager:
    """
    Manages LLM API costs and usage tracking.
    
    This is the ONLY component that should write to UsageRecord.
    """
    
    def __init__(self):
        """Initialize cost manager with pricing configuration."""
        self.pricing_config = self._load_pricing_config()
        self.metrics = get_metrics_collector()
    
    def _load_pricing_config(self) -> Dict[str, Dict[str, float]]:
        """
        Load pricing configuration from models.yaml.
        
        Returns:
            Dictionary mapping model names to pricing info
            Format: {model_name: {"cost_per_1k_tokens": float, "provider": str}}
        """
        config_path = Path("config/models.yaml")
        if not config_path.exists():
            # Default pricing if config doesn't exist
            return {
                "gpt-4o-mini": {"cost_per_1k_tokens": 0.15, "provider": "openai"},
                "gemini-2.0-flash-exp": {"cost_per_1k_tokens": 0.075, "provider": "gemini"},
                "gemini-2.5-flash": {"cost_per_1k_tokens": 0.075, "provider": "gemini"},
            }
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            pricing = {}
            for provider, models in config.get("models", {}).items():
                for model_name, model_config in models.items():
                    pricing[model_name] = {
                        "cost_per_1k_tokens": model_config.get("cost_per_1k_tokens", 0.0),
                        "provider": provider,
                    }
            
            return pricing
        except Exception as e:
            print(f"[WARNING] Failed to load pricing config: {e}")
            return {}
    
    def calculate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """
        Calculate cost for an LLM call.
        
        Args:
            model: Model name
            prompt_tokens: Input tokens
            completion_tokens: Output tokens
            
        Returns:
            Cost in USD
        """
        if model not in self.pricing_config:
            # Default pricing if model not found
            print(f"[WARNING] Model {model} not in pricing config, using default $0.10 per 1k tokens")
            cost_per_1k = 0.10
        else:
            cost_per_1k = self.pricing_config[model]["cost_per_1k_tokens"]
        
        total_tokens = prompt_tokens + completion_tokens
        cost = (total_tokens / 1000.0) * cost_per_1k
        
        return round(cost, 6)  # Round to 6 decimal places
    
    async def record_usage(
        self,
        tenant_id: str,
        user_id: str,
        model: str,
        provider: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost: Optional[float] = None,
        feature_tag: Optional[str] = None,
        request_id: Optional[str] = None,
        latency_ms: Optional[float] = None,
    ):
        """
        Record LLM usage and cost.
        
        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            model: Model name
            provider: Provider name
            prompt_tokens: Input tokens
            completion_tokens: Output tokens
            cost: Optional pre-calculated cost (will calculate if not provided)
            feature_tag: Optional feature identifier
            request_id: Optional request identifier
            latency_ms: Optional request latency
        """
        if cost is None:
            cost = self.calculate_cost(model, prompt_tokens, completion_tokens)
        
        total_tokens = prompt_tokens + completion_tokens
        
        # Record in metrics collector
        self.metrics.record_llm_call(
            tenant_id=tenant_id,
            user_id=user_id,
            model=model,
            provider=provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost,
            feature_tag=feature_tag,
            request_id=request_id,
            latency_ms=latency_ms,
        )
    
    async def check_budget(self, tenant_id: str, estimated_cost: float) -> bool:
        """
        Check if tenant has budget remaining.
        
        Args:
            tenant_id: Tenant identifier
            estimated_cost: Estimated cost for the operation
            
        Returns:
            True if budget allows, False otherwise
        """
        # TODO: Implement budget checking against tenant budget limits
        # For now, always allow
        return True
    
    async def get_usage_summary(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get usage summary for tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Dictionary with usage summary
        """
        summary = self.metrics.get_metrics_summary(tenant_id=tenant_id)
        return summary
    
    def get_model_pricing(self, model: str) -> Optional[Dict[str, Any]]:
        """
        Get pricing information for a model.
        
        Args:
            model: Model name
            
        Returns:
            Pricing info dict or None if not found
        """
        return self.pricing_config.get(model)


# Global singleton instance
_cost_manager: Optional[CostManager] = None


def get_cost_manager() -> CostManager:
    """Get or create global cost manager instance."""
    global _cost_manager
    if _cost_manager is None:
        _cost_manager = CostManager()
    return _cost_manager
