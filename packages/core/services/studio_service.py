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
import traceback

from config.settings import settings
from packages.core.llm import get_llm_client, get_model_for_task
from packages.core.llm._base import LLMProvider
from packages.core.prompts import load_prompt
from packages.core.rag.vectorstores.pinecone_store import PineconeVectorStore
from packages.core.image.dalle_client import DALLEClient


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
        self.vector_store = PineconeVectorStore(tenant_id)
    
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
            query_embedding = await self.vector_store.generate_embedding(query_text)
            
            # Query Pinecone with source_id filter to get chunks from selected sources
            filter_dict = {"source_id": {"$in": source_ids}}
            results = await self.vector_store.query_vectors(
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
                print(f"[STUDIO] Content will still be generated, but may be generic.")
                return ""
            
            print(f"[STUDIO] Successfully retrieved {len(context_parts)} chunks from {len(source_ids)} source(s)")
            return context
            
        except ValueError as e:
            # Configuration errors (missing API keys, etc.)
            print(f"[STUDIO] Configuration error retrieving context: {str(e)}")
            print(f"[STUDIO] Content will still be generated, but may be generic.")
            return ""
        except Exception as e:
            print(f"[STUDIO] Error retrieving context from sources: {type(e).__name__}: {str(e)}")
            print(f"[STUDIO] Traceback: {traceback.format_exc()}")
            print(f"[STUDIO] Content will still be generated, but may be generic.")
            return ""
    
    def _load_prompt_template(
        self,
        task_type: str,
        context: str,
        custom_instructions: Optional[str],
        template_map: Dict[str, str],
        default_template: str
    ) -> str:
        """Load prompt template with fallback."""
        template_path = template_map.get(task_type, default_template)
        try:
            return load_prompt(
                template_path,
                context=context or "",
                custom_instructions=custom_instructions or ""
            )
        except FileNotFoundError:
            print(f"[STUDIO] Prompt template not found: {template_path}, using fallback")
            return f"Generate a {task_type} based on: {context or 'general content'}"
    
    def _validate_generated_content(
        self,
        content: str,
        task_type: str,
        response: Any
    ) -> None:
        """Validate that content was actually generated."""
        if not content or not content.strip():
            model_name = response.model if hasattr(response, 'model') else 'unknown'
            raise ValueError(
                f"No content was generated for {task_type}. "
                f"The model may have been blocked, encountered an error, or returned empty content. "
                f"Model used: {model_name}. "
                f"Please check your API keys and try again."
            )
    
    def _clean_markdown_code_blocks(self, content: str) -> str:
        """Remove markdown code blocks from content."""
        if content.strip().startswith("```"):
            lines = content.strip().split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            return "\n".join(lines)
        return content
    
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
        prompt = self._load_prompt_template(
            task_type,
            context,
            custom_instructions,
            {
                "quiz": "studio/quiz_prompt.j2",
                "flashcards": "studio/flashcards_prompt.j2",
                "mind_map": "studio/mind_map_prompt.j2",
                "slide_deck": "studio/slide_deck_prompt.j2",
            },
            "studio/quiz_prompt.j2"
        )
        
        # Generate using LLM abstraction
        system_prompt = "You are a helpful educational content generator. Always return valid JSON or Markdown."
        try:
            response = await llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7
            )
        except Exception as e:
            error_msg = str(e)
            print(f"[STUDIO] [GPT] Generation failed: {type(e).__name__}: {error_msg}")
            raise ValueError(
                f"Failed to generate {task_type}: {error_msg}. "
                f"Please check your API keys and try again."
            )
        
        content = response.content or ""
        
        # Log response for debugging
        print(f"[STUDIO] [GPT] Generated content length: {len(content)} characters")
        if len(content) > 0:
            print(f"[STUDIO] [GPT] Content preview: {content[:100]}...")
        
        # Validate that content was actually generated
        self._validate_generated_content(content, task_type, response)
        
        # Clean up the content - remove markdown code blocks if present
        content = self._clean_markdown_code_blocks(content)
        
        # Validate content again after cleanup
        if not content or not content.strip():
            raise ValueError(
                f"No valid content was generated for {task_type} after processing. "
                f"The model response may have been empty or invalid."
            )
        
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
        prompt = self._load_prompt_template(
            task_type,
            context,
            custom_instructions,
            {
                "report": "studio/report_prompt.j2",
                "infographic": "studio/infographic_prompt.j2",
            },
            "studio/report_prompt.j2"
        )
        
        # Generate using LLM abstraction
        # For infographics, use a system prompt to ensure we get a direct DALL-E prompt
        system_prompt = None
        if task_type == "infographic":
            system_prompt = "You are a prompt engineer for DALL-E. Generate ONLY the prompt text that will be sent directly to DALL-E. Do not include any explanations, descriptions, or meta-commentary. Just output the prompt itself."
        
        try:
            response = await llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7
            )
        except Exception as e:
            error_msg = str(e)
            print(f"[STUDIO] [GEMINI] Generation failed: {type(e).__name__}: {error_msg}")
            # If Gemini is not available (common in region/plan mismatches), transparently fall back to OpenAI
            # so Studio tools still work.
            if "404" in error_msg or "not found" in error_msg.lower() or "not supported" in error_msg.lower():
                print(f"[STUDIO] [FALLBACK] Gemini unavailable for {task_type}. Falling back to OpenAI (gpt-4o-mini).")
                try:
                    openai_client = get_llm_client(
                        provider=LLMProvider.OPENAI,
                        model="gpt-4o-mini",
                        temperature=0.7
                    )
                    fallback_system_prompt = "You are a helpful educational content generator. Return clear Markdown."
                    response = await openai_client.generate(
                        prompt=prompt,
                        system_prompt=fallback_system_prompt,
                        temperature=0.7
                    )
                except Exception as openai_error:
                    openai_msg = str(openai_error)
                    raise ValueError(
                        f"Gemini model not available in your region/plan (original error: {error_msg}). "
                        f"Also failed to fall back to OpenAI: {openai_msg}. "
                        f"Please check your OPENAI_API_KEY and GEMINI_API_KEY configuration."
                    )
            else:
                raise ValueError(
                    f"Failed to generate {task_type}: {error_msg}. "
                    f"Please check your API keys and try again."
                )
        
        content = response.content or ""
        
        # Log response for debugging
        print(f"[STUDIO] [GEMINI] Generated content length: {len(content)} characters")
        if len(content) > 0:
            print(f"[STUDIO] [GEMINI] Content preview: {content[:100]}...")
        
        # Validate that content was actually generated
        self._validate_generated_content(content, task_type, response)
        
        # For infographics, generate an actual image
        if task_type == "infographic":
            try:
                # Clean up the prompt - remove markdown code blocks, quotes, and common prefixes
                dalle_prompt = content.strip()
                
                # Remove markdown code blocks if present
                if dalle_prompt.startswith("```"):
                    lines = dalle_prompt.split("\n")
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    dalle_prompt = "\n".join(lines).strip()
                
                # Remove common prefixes that LLMs might add
                prefixes_to_remove = [
                    "here's the prompt:",
                    "here is the prompt:",
                    "dall-e prompt:",
                    "prompt:",
                    "image prompt:",
                    "the prompt is:",
                    "the dall-e prompt:",
                ]
                dalle_prompt_lower = dalle_prompt.lower()
                for prefix in prefixes_to_remove:
                    if dalle_prompt_lower.startswith(prefix):
                        dalle_prompt = dalle_prompt[len(prefix):].strip()
                        break
                
                # Remove quotes if the entire prompt is wrapped in them
                if (dalle_prompt.startswith('"') and dalle_prompt.endswith('"')) or \
                   (dalle_prompt.startswith("'") and dalle_prompt.endswith("'")):
                    dalle_prompt = dalle_prompt[1:-1].strip()
                
                # ALWAYS generate an image for infographics - even if the text looks like a prompt
                # The LLM might generate a design brief, which we'll convert to a DALL-E prompt
                
                # Check if it already starts with a proper prompt format
                is_already_prompt = dalle_prompt_lower.startswith(('a detailed', 'an educational', 'a comprehensive', 'an infographic'))
                
                # Check for design brief indicators - section descriptions, panel labels, etc.
                has_sections = any(indicator in dalle_prompt_lower for indicator in [
                    "composition and sections:",
                    "top section:",
                    "top panel",
                    "the top panel",
                    "middle section:",
                    "middle left section:",
                    "middle right section:",
                    "the central section",
                    "bottom section:",
                    "lower panel",
                    "the lower panel",
                    "overall design elements:",
                    "labeled '",
                    "titled '",
                    "panel, labeled",
                    "section titled",
                    "panel titled",
                    "illustrates a",
                    "depicts a",
                    "features a",
                    "showcases a",
                ])
                
                # Check if it's a very long description (design briefs are usually longer than 400 chars)
                is_long_description = len(dalle_prompt) > 400
                
                # Check if it contains narrative/descriptive language typical of design briefs
                has_narrative = any(phrase in dalle_prompt_lower for phrase in [
                    "is presented",
                    "is that of",
                    "utilizing a",
                    "illustrates",
                    "depicts",
                    "showcases",
                    "represents",
                    "symbolizing",
                ])
                
                # If it has section indicators, is long, or has narrative language, convert it
                # This catches design briefs even if they start with "A detailed educational infographic"
                needs_conversion = has_sections or (is_long_description and has_narrative)
                
                if needs_conversion:
                    # Convert design brief to DALL-E prompt
                    print(f"[STUDIO] [INFographic] Detected design brief format, converting to DALL-E prompt...")
                    print(f"[STUDIO] [INFographic] Original length: {len(dalle_prompt)} characters")
                    
                    # Extract title if present
                    title_match = re.search(r"titled ['\"]([^'\"]+)['\"]", dalle_prompt, re.IGNORECASE)
                    title = title_match.group(1) if title_match else None
                    
                    # Clean up the text - remove panel/section labels and convert to flowing description
                    # Replace common patterns
                    cleaned = dalle_prompt
                    
                    # Remove explicit section/panel labels but keep the content
                    cleaned = re.sub(r"(?:^|\n)\s*(?:The\s+)?(?:top|middle|central|lower|bottom)\s+(?:panel|section)[,:\s]*", " ", cleaned, flags=re.IGNORECASE | re.MULTILINE)
                    cleaned = re.sub(r"(?:^|\n)\s*(?:labeled|titled)\s+['\"][^'\"]+['\"][,:\s]*", " ", cleaned, flags=re.IGNORECASE | re.MULTILINE)
                    cleaned = re.sub(r"panel,\s*labeled", "showing", cleaned, flags=re.IGNORECASE)
                    cleaned = re.sub(r"section\s+titled", "section showing", cleaned, flags=re.IGNORECASE)
                    
                    # Remove redundant phrases
                    cleaned = re.sub(r"\bThe infographic (features|is|shows|presents)\b", "", cleaned, flags=re.IGNORECASE)
                    cleaned = re.sub(r"\bThe design uses\b", "using", cleaned, flags=re.IGNORECASE)
                    cleaned = re.sub(r"\bis presented\b", "shows", cleaned, flags=re.IGNORECASE)
                    cleaned = re.sub(r"\bis that of\b", "in", cleaned, flags=re.IGNORECASE)
                    
                    # Clean up extra whitespace
                    cleaned = ' '.join(cleaned.split())
                    
                    # Remove quotes around title mentions if they're redundant
                    if title:
                        cleaned = re.sub(rf"titled\s+['\"]{re.escape(title)}['\"]", f"titled '{title}'", cleaned, flags=re.IGNORECASE)
                    
                    # Ensure it flows as a single description
                    # Remove excessive periods and create smooth flow
                    cleaned = re.sub(r'\.\s+([A-Z])', r'. \1', cleaned)  # Ensure space after periods
                    
                    # DALL-E 3 supports up to 4000 characters, but we'll keep it reasonable (2000 chars max)
                    # Keep the most important descriptive content
                    if len(cleaned) > 1800:
                        # Keep first 1500 chars (usually contains title and main sections)
                        # Then add a summary ending
                        cleaned = cleaned[:1800].rsplit('.', 1)[0] + ". The design uses a clean, modern layout with vibrant colors, clear labels, text boxes, diagrams, and illustrations in a science textbook illustration style."
                    
                    # Create the final DALL-E prompt
                    if title:
                        dalle_prompt = f"A detailed educational infographic titled '{title}' showing {cleaned}. The design uses a clean, modern layout with vibrant colors, clear labels, text boxes, diagrams, and illustrations in a science textbook illustration style."
                    else:
                        dalle_prompt = f"A detailed educational infographic showing {cleaned}. The design uses a clean, modern layout with vibrant colors, clear labels, text boxes, diagrams, and illustrations in a science textbook illustration style."
                    
                    print(f"[STUDIO] [INFographic] Converted brief to DALL-E prompt (length: {len(dalle_prompt)})")
                    print(f"[STUDIO] [INFographic] Title extracted: {title if title else 'None'}")
                elif not is_already_prompt:
                    # If it doesn't start with a description, ensure it does
                    if not dalle_prompt_lower.startswith(('a ', 'an ', 'the ')):
                        dalle_prompt = f"A detailed educational infographic showing {dalle_prompt}"
                
                # DALL-E 3 supports up to 4000 characters, but keep it under 2000 for best results
                if len(dalle_prompt) > 2000:
                    # Truncate at a sentence boundary if possible
                    truncate_point = dalle_prompt[:2000].rfind('.')
                    if truncate_point > 1500:
                        dalle_prompt = dalle_prompt[:truncate_point + 1]
                    else:
                        dalle_prompt = dalle_prompt[:2000]
                
                print(f"[STUDIO] [INFographic] Final DALL-E prompt (length: {len(dalle_prompt)}):")
                print(f"[STUDIO] [INFographic] {dalle_prompt[:500]}...")
                
                # Generate image using DALL-E
                print(f"[STUDIO] [INFographic] Using DALL-E for image generation...")
                dalle_client = DALLEClient()
                image_result = await dalle_client.generate_image(
                    prompt=dalle_prompt,
                    model="dall-e-3",
                    size="1792x1024",  # Wide format for infographics
                    quality="hd"
                )
                
                image_url = image_result.get("url")
                revised_prompt = image_result.get("revised_prompt")
                
                print(f"[STUDIO] [INFographic] ✅ Image generated successfully!")
                print(f"[STUDIO] [INFographic] Image URL: {image_url}")
                print(f"[STUDIO] [INFographic] Revised prompt: {revised_prompt[:200] if revised_prompt else 'N/A'}...")
                
                if not image_url:
                    raise ValueError("DALL-E returned no image URL")
                
                return {
                    "task_type": task_type,
                    "content": content,  # Keep the original prompt description
                    "image_url": image_url,
                    "revised_prompt": revised_prompt,
                }
            except Exception as e:
                error_msg = str(e)
                print(f"[STUDIO] [INFographic] Image generation failed: {error_msg}")
                print(f"[STUDIO] [INFographic] Traceback: {traceback.format_exc()}")
                # Return text content even if image generation fails
                return {
                    "task_type": task_type,
                    "content": content,
                    "image_error": f"Image generation failed: {error_msg}",
                }
        
        return {
            "task_type": task_type,
            "content": content,
        }


