"""
Budget Enforcer

Thin wrapper that delegates to CostManager.
Enforces budget limits before allowing LLM operations.
"""

from config.settings import settings
from packages.core.guardrails.cost_manager import CostManager
from packages.core.guardrails.exceptions import BudgetExceededError


class BudgetEnforcer:
    """
    Enforces budget limits for LLM operations.
    
    Delegates all cost operations to CostManager.
    """
    
    def __init__(self):
        self.cost_manager = CostManager()
    
    async def enforce_budget(self, tenant_id: str, estimated_cost: float = 0.0) -> None:
        """Raise BudgetExceededError when the tenant monthly cap would be exceeded."""
        if not getattr(settings, "ENABLE_BUDGET_ENFORCEMENT", False):
            return
        ok = await self.cost_manager.check_budget(tenant_id, estimated_cost)
        if ok:
            return
        spent = self.cost_manager.get_monthly_spend_usd(tenant_id)
        cap = float(getattr(settings, "TENANT_MONTHLY_BUDGET_USD", 100.0))
        raise BudgetExceededError(
            f"Monthly LLM budget exceeded (${spent:.4f} spent, cap ${cap:.2f})."
        )

    def budget_status(self, tenant_id: str) -> dict:
        """Return current-month spend vs cap for admin dashboards."""
        cap = float(getattr(settings, "TENANT_MONTHLY_BUDGET_USD", 100.0))
        spent = self.cost_manager.get_monthly_spend_usd(tenant_id)
        remaining = max(0.0, cap - spent)
        return {
            "enabled": bool(getattr(settings, "ENABLE_BUDGET_ENFORCEMENT", False)),
            "monthly_cap_usd": cap,
            "spent_usd": spent,
            "remaining_usd": remaining,
            "blocked": spent >= cap,
        }


