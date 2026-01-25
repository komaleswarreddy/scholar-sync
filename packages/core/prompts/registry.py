"""
Prompt Registry

Tracks prompt versions and metadata.
"""

from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PromptMetadata:
    """Metadata for a prompt template."""
    name: str
    version: str
    description: str
    created_at: datetime
    updated_at: datetime
    variables: Dict[str, str]  # Variable name -> description


class PromptRegistry:
    """
    Registry for prompt templates.
    
    Tracks versions, metadata, and usage statistics.
    """
    
    def __init__(self):
        self._prompts: Dict[str, PromptMetadata] = {}
    
    def register(
        self,
        name: str,
        version: str,
        description: str,
        variables: Dict[str, str],
    ):
        """Register a prompt template."""
        now = datetime.now()
        metadata = PromptMetadata(
            name=name,
            version=version,
            description=description,
            created_at=now,
            updated_at=now,
            variables=variables,
        )
        self._prompts[name] = metadata
    
    def get(self, name: str) -> Optional[PromptMetadata]:
        """Get prompt metadata."""
        return self._prompts.get(name)
    
    def list_all(self) -> Dict[str, PromptMetadata]:
        """List all registered prompts."""
        return self._prompts.copy()
