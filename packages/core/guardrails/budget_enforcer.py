"""
Budget Enforcer

Thin wrapper that delegates to CostManager.
Enforces budget limits before allowing LLM operations.
"""

from packages.core.guardrails.cost_manager import CostManager

# TODO: Implement budget enforcement
# - Check budget before LLM calls
# - Raise exceptions if budget exceeded
# - Provide budget status to users


class BudgetEnforcer:
    """
    Enforces budget limits for LLM operations.
    
    Delegates all cost operations to CostManager.
    """
    
    def __init__(self):
        self.cost_manager = CostManager()
    
    async def enforce_budget(self, tenant_id: str, estimated_cost: float):
        """Enforce budget before operation."""
        # TODO: Implement budget enforcement
        pass


