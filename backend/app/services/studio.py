"""
Studio Service

Handles generative tasks with smart model routing.
Routes to optimal model based on task type.
"""

from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import google.generativeai as genai
import openai
import json

from app.core.config import settings
from app.services.vector import VectorService

# Lazy configuration - will be configured when needed
_gemini_configured = False
_openai_configured = False

def configure_gemini():
    """Lazy configuration of Gemini API."""
    global _gemini_configured
    if not _gemini_configured:
        if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your-gemini-api-key":
            raise ValueError("Gemini API key not configured. Please set GEMINI_API_KEY in .env")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _gemini_configured = True

def configure_openai():
    """Lazy configuration of OpenAI API."""
    global _openai_configured
    if not _openai_configured:
        if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "your-openai-api-key":
            raise ValueError("OpenAI API key not configured. Please set OPENAI_API_KEY in .env")
        openai.api_key = settings.OPENAI_API_KEY
        _openai_configured = True


class StudioService:
    """
    Service for Studio generation tasks.
    
    Smart Routing:
    - Structured tasks (quiz, flashcards, mind_map, slide_deck) -> GPT-4o-mini
    - Content-heavy tasks (report, infographic) -> Gemini 1.5 Flash
    """
    
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.vector_service = VectorService(tenant_id)
        self._gemini_model = None
    
    @property
    def gemini_model(self):
        """Lazy initialization of Gemini model."""
        if self._gemini_model is None:
            configure_gemini()
            # Use gemini-2.5-flash (newer version) or fallback to gemini-1.5-flash
            try:
                self._gemini_model = genai.GenerativeModel("gemini-2.5-flash")
            except:
                self._gemini_model = genai.GenerativeModel("gemini-1.5-flash")
        return self._gemini_model
    
    async def generate(
        self,
        task_type: str,
        source_ids: list,
        custom_instructions: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate Studio content based on task type.
        
        Args:
            task_type: Type of generation (quiz, flashcards, etc.)
            source_ids: List of source IDs to use
            custom_instructions: Optional custom instructions
            
        Returns:
            Dictionary with generated content
        """
        # Retrieve context from sources
        context = await self._get_context_from_sources(source_ids)
        
        # Route to appropriate model
        if task_type in ["quiz", "flashcards", "mind_map", "slide_deck"]:
            # Structured output -> GPT-4o-mini
            return await self._generate_with_gpt4o_mini(task_type, context, custom_instructions)
        else:
            # Content-heavy -> Gemini 1.5 Flash
            return await self._generate_with_gemini(task_type, context, custom_instructions)
    
    async def _get_context_from_sources(self, source_ids: list) -> str:
        """Retrieve text content from sources for context."""
        # Query Pinecone for chunks from these sources
        # For simplicity, get all chunks from sources (in production, use better retrieval)
        context_parts = []
        # Implementation would query Pinecone with source_id filter
        return "\n\n".join(context_parts)
    
    async def _generate_with_gpt4o_mini(
        self,
        task_type: str,
        context: str,
        custom_instructions: Optional[str],
    ) -> Dict[str, Any]:
        """Generate structured content with GPT-4o-mini."""
        configure_openai()
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Build prompt based on task type
        prompts = {
            "quiz": f"""Generate a quiz based on the following content. Return JSON with this structure:
{{
  "title": "Quiz Title",
  "questions": [
    {{
      "question": "Question text",
      "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
      "correct_answer": "Correct option",
      "explanation": "Explanation text"
    }}
  ]
}}

Content:
{context}

{custom_instructions or ""}
""",
            "flashcards": f"""Generate flashcards based on the content. Return JSON array:
[
  {{"front": "Term", "back": "Definition"}},
  ...
]

Content:
{context}
""",
            "mind_map": f"""Generate a mind map in Markdown format with hierarchical structure:
# Main Topic
## Subtopic 1
- Point 1
- Point 2
## Subtopic 2
...

Content:
{context}
""",
            "slide_deck": f"""Generate a slide deck outline in Markdown:
# Slide 1: Title
Content

# Slide 2: Topic
Content
...

Content:
{context}
""",
        }
        
        prompt = prompts.get(task_type, prompts["quiz"])
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful educational content generator. Always return valid JSON or Markdown."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
        
        content = response.choices[0].message.content
        
        # Parse and return
        if task_type in ["quiz", "flashcards"]:
            data = json.loads(content)
            return {"task_type": task_type, "data": data}
        else:
            return {"task_type": task_type, "content": content}
    
    async def _generate_with_gemini(
        self,
        task_type: str,
        context: str,
        custom_instructions: Optional[str],
    ) -> Dict[str, Any]:
        """Generate content-heavy tasks with Gemini 1.5 Flash."""
        prompts = {
            "report": f"""Generate a comprehensive report based on the following content. Include:
- Executive Summary
- Key Points
- Detailed Analysis
- Conclusions

Content:
{context}

{custom_instructions or ""}
""",
            "infographic": f"""Generate a visual brief description for an infographic based on:
- Main visual elements
- Data points to highlight
- Layout suggestions
- Color scheme recommendations

Content:
{context}
""",
        }
        
        prompt = prompts.get(task_type, prompts["report"])
        
        response = self.gemini_model.generate_content(prompt)
        
        return {
            "task_type": task_type,
            "content": response.text,
        }

