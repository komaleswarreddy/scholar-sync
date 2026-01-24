"""
Prompt Registry

Tracks prompt versions and metadata.
Enables A/B testing and prompt versioning.
"""

from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PromptVersion:
    """Metadata for a prompt version."""
    version: str
    template_path: str
    description: str
    created_at: datetime
    is_active: bool = True
    metadata: Optional[Dict] = None


class PromptRegistry:
    """
    Registry for prompt versions.
    
    Tracks which prompts are active, their versions, and metadata.
    """
    
    def __init__(self):
        self._prompts: Dict[str, PromptVersion] = {}
    
    def register(
        self,
        name: str,
        version: str,
        template_path: str,
        description: str = "",
        metadata: Optional[Dict] = None
    ):
        """
        Register a prompt version.
        
        Args:
            name: Prompt name (e.g., "quiz", "rag_chat")
            version: Version string (e.g., "v1", "v2")
            template_path: Path to template file
            description: Description of the prompt
            metadata: Additional metadata
        """
        key = f"{name}:{version}"
        self._prompts[key] = PromptVersion(
            version=version,
            template_path=template_path,
            description=description,
            created_at=datetime.now(),
            is_active=True,
            metadata=metadata or {}
        )
    
    def get_active_version(self, name: str) -> Optional[PromptVersion]:
        """Get the active version of a prompt."""
        # Find latest active version
        versions = [
            pv for key, pv in self._prompts.items()
            if key.startswith(f"{name}:") and pv.is_active
        ]
        if not versions:
            return None
        # Return most recent
        return max(versions, key=lambda pv: pv.created_at)
    
    def get_template_path(self, name: str, version: Optional[str] = None) -> Optional[str]:
        """
        Get template path for a prompt.
        
        Args:
            name: Prompt name
            version: Specific version (if None, returns active version)
            
        Returns:
            Template path or None
        """
        if version:
            key = f"{name}:{version}"
            prompt = self._prompts.get(key)
        else:
            prompt = self.get_active_version(name)
        
        return prompt.template_path if prompt else None


# Global registry instance
_registry = PromptRegistry()

def get_registry() -> PromptRegistry:
    """Get the global prompt registry."""
    return _registry
