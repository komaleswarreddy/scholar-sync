"""
Studio Service

Handles generative tasks with smart model routing.
Routes to optimal model based on task type.

Uses LLM abstraction layer and prompt templates.
"""

from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import json
import re

from app.core.config import settings
from app.core.llm import get_llm_client, get_model_for_task, LLMClient
from app.prompts import load_prompt
from app.services.vector import VectorService


class StudioService:
    """
    Service for Studio generation tasks.
    
    Smart Routing:
    - Structured tasks (quiz, flashcards, mind_map, slide_deck) -> GPT-4o-mini
    - Content-heavy tasks (report, infographic) -> Gemini 1.5 Flash
    """
    
    def __init__(self, db: AsyncSession, tenant_id: str, user_id: str = None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.vector_service = VectorService(tenant_id)
    
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
        
        # Warn if context is empty (but allow generation to proceed)
        if not context or not context.strip():
            print(f"[WARNING] Empty context for sources: {source_ids}. Generation may produce generic content.")
        
        # Route to appropriate model
        if task_type in ["quiz", "flashcards", "mind_map", "slide_deck"]:
            # Structured output -> GPT-4o-mini
            return await self._generate_with_gpt4o_mini(task_type, context, custom_instructions)
        else:
            # Content-heavy -> Gemini 1.5 Flash
            return await self._generate_with_gemini(task_type, context, custom_instructions)
    
    async def _get_context_from_sources(self, source_ids: list) -> str:
        """Retrieve text content from sources for context."""
        if not source_ids:
            print(f"[STUDIO] No source IDs provided")
            return ""
        
        try:
            # Generate a generic embedding to retrieve relevant chunks from the sources
            # We use a generic query to get content from the selected sources
            query_text = "Generate quiz questions based on this content"
            query_embedding = await self.vector_service.generate_embedding(query_text)
            
            # Query Pinecone with source_id filter to get chunks from selected sources
            filter_dict = {"source_id": {"$in": source_ids}}
            results = await self.vector_service.query_vectors(
                query_embedding=query_embedding,
                top_k=settings.TOP_K_CHUNKS * 2,  # Get more chunks for better context
                filter=filter_dict,
            )
            
            # Build context from retrieved chunks
            context_parts = []
            for match in results.get("matches", []):
                chunk_text = match.get("metadata", {}).get("text", "")
                if chunk_text:
                    context_parts.append(chunk_text)
            
            context = "\n\n".join(context_parts)
            
            if not context or not context.strip():
                print(f"[STUDIO] WARNING: No content retrieved from sources: {source_ids}")
                print(f"[STUDIO] This might mean:")
                print(f"[STUDIO]   1. Sources have not been processed/ingested yet")
                print(f"[STUDIO]   2. Pinecone is not configured or not accessible")
                print(f"[STUDIO]   3. No vectors exist for these source IDs")
                print(f"[STUDIO] Quiz will still be generated, but may be generic.")
                return ""
            
            print(f"[STUDIO] Successfully retrieved {len(context_parts)} chunks from {len(source_ids)} source(s)")
            return context
            
        except ValueError as e:
            # Configuration errors (missing API keys, etc.)
            error_msg = str(e)
            print(f"[STUDIO] Configuration error retrieving context: {error_msg}")
            print(f"[STUDIO] Quiz will still be generated, but may be generic.")
            return ""
        except Exception as e:
            import traceback
            print(f"[STUDIO] Error retrieving context from sources: {type(e).__name__}: {str(e)}")
            print(f"[STUDIO] Traceback: {traceback.format_exc()}")
            print(f"[STUDIO] Quiz will still be generated, but may be generic.")
            # Return empty context rather than failing completely
            return ""
    
    async def _generate_with_gpt4o_mini(
        self,
        task_type: str,
        context: str,
        custom_instructions: Optional[str],
    ) -> Dict[str, Any]:
        """Generate structured content with GPT-4o-mini using LLM abstraction."""
        # Get LLM client using factory
        provider, model = get_model_for_task(task_type)
        llm_client = get_llm_client(provider=provider, model=model, temperature=0.7)
        
        # Load prompt template
        prompt_template_map = {
            "quiz": "studio/quiz_prompt.j2",
            "flashcards": "studio/flashcards_prompt.j2",
            "mind_map": "studio/mind_map_prompt.j2",
            "slide_deck": "studio/slide_deck_prompt.j2",
        }
        
        template_path = prompt_template_map.get(task_type, "studio/quiz_prompt.j2")
        
        try:
            prompt = load_prompt(
                template_path,
                context=context or "",
                custom_instructions=custom_instructions or ""
            )
        except FileNotFoundError as e:
            print(f"[STUDIO] Prompt template not found: {template_path}, using fallback")
            # Fallback to inline prompt if template missing
            prompt = f"Generate a {task_type} based on: {context or 'general content'}"
        
        # Generate using LLM abstraction
        system_prompt = "You are a helpful educational content generator. Always return valid JSON or Markdown."
        response = await llm_client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.7
        )
        
        content = response.content
        
        # Clean up the content - remove markdown code blocks if present
        if content.strip().startswith("```"):
            # Remove markdown code blocks
            lines = content.strip().split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)
        
        # Parse and return
        if task_type in ["quiz", "flashcards"]:
            try:
                data = json.loads(content)
                print(f"[STUDIO] Successfully parsed {task_type} response")
                return {"task_type": task_type, "data": data}
            except json.JSONDecodeError as e:
                print(f"[STUDIO] Failed to parse JSON response: {str(e)}")
                print(f"[STUDIO] Response content: {content[:500]}...")
                # Try to extract JSON from the response
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    try:
                        data = json.loads(json_match.group())
                        print(f"[STUDIO] Successfully extracted JSON from response")
                        return {"task_type": task_type, "data": data}
                    except:
                        pass
                raise ValueError(f"Failed to parse {task_type} response as JSON. Response: {content[:200]}")
        else:
            return {"task_type": task_type, "content": content}
    
    async def _generate_with_gemini(
        self,
        task_type: str,
        context: str,
        custom_instructions: Optional[str],
    ) -> Dict[str, Any]:
        """Generate content-heavy tasks with Gemini using LLM abstraction."""
        # Get LLM client using factory
        provider, model = get_model_for_task(task_type)
        llm_client = get_llm_client(provider=provider, model=model, temperature=0.7)
        
        # Load prompt template
        prompt_template_map = {
            "report": "studio/report_prompt.j2",
            "infographic": "studio/infographic_prompt.j2",
        }
        
        template_path = prompt_template_map.get(task_type, "studio/report_prompt.j2")
        
        try:
            prompt = load_prompt(
                template_path,
                context=context or "",
                custom_instructions=custom_instructions or ""
            )
        except FileNotFoundError as e:
            print(f"[STUDIO] Prompt template not found: {template_path}, using fallback")
            # Fallback to inline prompt if template missing
            prompt = f"Generate a {task_type} based on: {context or 'general content'}"
        
        # Generate using LLM abstraction
        response = await llm_client.generate(
            prompt=prompt,
            temperature=0.7
        )
        
        return {
            "task_type": task_type,
            "content": response.content,
        }

