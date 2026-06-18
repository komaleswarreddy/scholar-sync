"""Guardrail exceptions."""


class BudgetExceededError(Exception):
    """Raised when a tenant exceeds its monthly LLM budget cap."""
