"""
Base Skill Interface

Abstract base class for all skill implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseSkill(ABC):
    """Base class for all skills."""
    
    def __init__(self):
        pass
    
    @abstractmethod
    async def execute(self, context: str, **kwargs) -> Dict[str, Any]:
        """Execute the skill."""
        pass


