"""
Task Router

Routes tasks to appropriate handlers and models.
"""

from typing import Any, Dict

from packages.core.llm.factory import get_model_for_task


class TaskRouter:
    """Routes tasks to appropriate handlers."""
    
    def __init__(self):
        pass
    
    def route(self, task_type: str) -> Dict[str, Any]:
        """Route task to provider/model via the shared LLM factory."""
        provider, model = get_model_for_task(task_type)
        provider_name = provider.value if hasattr(provider, "value") else str(provider)
        return {
            "task_type": task_type,
            "provider": provider_name,
            "model": model,
        }


