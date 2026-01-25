"""
Prompt Loader

Loads and renders prompt templates using Jinja2.
Supports template variables and versioning.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, TemplateNotFound


class PromptLoader:
    """
    Loads and renders prompt templates.
    
    Templates are stored in packages/core/prompts/templates/
    and use Jinja2 syntax for variables.
    """
    
    def __init__(self, template_dir: Optional[str] = None):
        """
        Initialize prompt loader.
        
        Args:
            template_dir: Directory containing templates (defaults to packages/core/prompts/templates)
        """
        if template_dir is None:
            # Get the prompts directory (parent of this file)
            base_dir = Path(__file__).parent
            template_dir = str(base_dir / "templates")
        
        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False  # We're not rendering HTML
        )
    
    def load(self, template_path: str, **kwargs) -> str:
        """
        Load and render a prompt template.
        
        Args:
            template_path: Path to template relative to templates directory
                          (e.g., "studio/quiz_prompt.j2")
            **kwargs: Variables to pass to template
            
        Returns:
            Rendered prompt string
            
        Raises:
            TemplateNotFound: If template doesn't exist
        """
        try:
            template = self.env.get_template(template_path)
            return template.render(**kwargs)
        except TemplateNotFound:
            raise FileNotFoundError(
                f"Prompt template not found: {template_path}. "
                f"Looked in: {self.template_dir}"
            )
    
    def load_raw(self, template_path: str) -> str:
        """
        Load template without rendering (for inspection).
        
        Args:
            template_path: Path to template
            
        Returns:
            Raw template content
        """
        template = self.env.get_template(template_path)
        return template.source


# Global prompt loader instance
_default_loader = None

def get_loader() -> PromptLoader:
    """Get the default prompt loader instance."""
    global _default_loader
    if _default_loader is None:
        _default_loader = PromptLoader()
    return _default_loader

def load_prompt(template_path: str, **kwargs) -> str:
    """
    Convenience function to load a prompt.
    
    Args:
        template_path: Path to template
        **kwargs: Template variables
        
    Returns:
        Rendered prompt
    """
    return get_loader().load(template_path, **kwargs)
