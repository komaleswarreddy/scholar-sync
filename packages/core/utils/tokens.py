"""
Token Utilities

Utilities for token counting and estimation.
"""

# TODO: Implement token counting
# - Count tokens in text
# - Estimate token usage
# - Support multiple tokenizers


def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """Count tokens in text."""
    # TODO: Implement token counting
    # Rough estimate: 1 token ≈ 4 characters
    return len(text) // 4

