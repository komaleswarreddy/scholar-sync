"""
RAG Service

Handles Retrieval-Augmented Generation for chat.
Uses Gemini 1.5 Flash for context-heavy tasks with streaming support.
"""

from typing import List, Dict, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
import google.generativeai as genai

from app.core.config import settings
from app.services.vector import VectorService
from app.schemas.chat import ChatMessage, Citation

# Lazy Gemini configuration
_gemini_configured = False

def configure_gemini():
    """Lazy configuration of Gemini API."""
    global _gemini_configured
    if not _gemini_configured:
        if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your-gemini-api-key":
            raise ValueError("Gemini API key not configured. Please set GEMINI_API_KEY in .env")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _gemini_configured = True


class RAGService:
    """
    Service for RAG-based chat with streaming.
    
    Process:
    1. Embed user query
    2. Query Pinecone with tenant namespace and source filters
    3. Retrieve top K chunks
    4. Construct prompt with context
    5. Stream response from Gemini 1.5 Flash
    6. Extract citations from response
    """
    
    def __init__(self, db: AsyncSession, tenant_id: str, user_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.vector_service = VectorService(tenant_id)
        self._model = None
    
    @property
    def model(self):
        """Lazy initialization of Gemini model."""
        if self._model is None:
            configure_gemini()
            # Use gemini-2.5-flash (newer version) or fallback to gemini-1.5-flash
            try:
                self._model = genai.GenerativeModel("gemini-2.5-flash")
            except:
                self._model = genai.GenerativeModel("gemini-1.5-flash")
        return self._model
    
    async def stream_chat(
        self,
        message: str,
        history: List[ChatMessage],
        active_source_ids: List[str],
    ) -> AsyncGenerator[Dict, None]:
        """
        Stream chat response with RAG.
        
        Yields:
            Dictionary with 'event' and 'data' keys for SSE
        """
        # 1. Embed query
        query_embedding = await self.vector_service.generate_embedding(message)
        
        # 2. Query Pinecone (with tenant namespace and source filter)
        filter_dict = {"source_id": {"$in": active_source_ids}} if active_source_ids else None
        results = await self.vector_service.query_vectors(
            query_embedding=query_embedding,
            top_k=settings.TOP_K_CHUNKS,
            filter=filter_dict,
        )
        
        # 3. Build context from retrieved chunks (already sorted by relevance/score from Pinecone)
        # First, collect unique source_ids to fetch their titles
        unique_source_ids = list(set([match["metadata"]["source_id"] for match in results["matches"]]))
        
        # Fetch source titles from database
        from sqlalchemy import select
        from app.models.source import Source
        import uuid as uuid_lib
        
        source_titles_map = {}
        if unique_source_ids:
            tenant_uuid = uuid_lib.UUID(self.tenant_id)
            source_uuids = [uuid_lib.UUID(sid) for sid in unique_source_ids]
            result = await self.db.execute(
                select(Source.id, Source.title).where(
                    Source.id.in_(source_uuids),
                    Source.tenant_id == tenant_uuid
                )
            )
            sources = result.all()
            for source in sources:
                source_titles_map[str(source.id)] = source.title
            print(f"[RAG] Loaded {len(sources)} source titles: {list(source_titles_map.values())}")
        
        context_chunks = []
        citations = []
        # Filter to only include citations with score >= 0.50 (50%)
        MIN_SCORE_THRESHOLD = 0.50
        citation_index = 0
        
        for match in results["matches"]:
            chunk_text = match["metadata"]["text"]
            source_id = match["metadata"]["source_id"]
            score = match.get("score", 0)
            
            # Only include citations with score >= 50%
            if score >= MIN_SCORE_THRESHOLD:
                citation_index += 1
                source_title = source_titles_map.get(source_id, None)
                # Note: chunks are numbered [1], [2], etc. in order of relevance (highest score first)
                context_chunks.append(f"[{citation_index}] {chunk_text}")
                citations.append({
                    "source_id": source_id,
                    "chunk_id": match["id"],
                    "text": chunk_text,  # Full text, not preview
                    "score": score,
                    "source_title": source_title,  # Include source title
                })
        
        print(f"[RAG] Filtered citations: {len(citations)} out of {len(results['matches'])} matches (score >= {MIN_SCORE_THRESHOLD})")
        
        # If no citations meet the threshold, include at least the top result to ensure we have context
        if len(citations) == 0 and len(results["matches"]) > 0:
            print(f"[RAG] WARNING: No citations met {MIN_SCORE_THRESHOLD} threshold. Including top result as fallback.")
            top_match = results["matches"][0]
            chunk_text = top_match["metadata"]["text"]
            source_id = top_match["metadata"]["source_id"]
            score = top_match.get("score", 0)
            source_title = source_titles_map.get(source_id, None)
            context_chunks.append(f"[1] {chunk_text}")
            citations.append({
                "source_id": source_id,
                "chunk_id": top_match["id"],
                "text": chunk_text,
                "score": score,
                "source_title": source_title,
            })
        
        context = "\n\n".join(context_chunks)
        
        # 4. Construct prompt with context
        if context:
            # If we have context from sources, include it in the prompt
            full_prompt = f"""You are a helpful AI assistant for students. Answer questions based ONLY on the provided context.

Context (chunks numbered [1], [2], [3]... in order of relevance - [1] is most relevant):
{context}

Answer Format Instructions:
1. Start your answer with a clear, complete sentence that directly answers the question. For example, if asked "what are NULL values", start with "NULL value is..." or "NULL values are..." - be explicit and clear from the first sentence.
2. Use the most relevant chunk(s) - typically [1] or [2] - to provide the direct answer.
3. After the direct answer, you can mention alternative approaches or related information if applicable.
4. Only cite chunk numbers [1], [2], etc. that actually contain the information you are stating. Do NOT cite chunks that do not contain the information.
5. Use proper formatting with Markdown:
   - Use **bold** for emphasis
   - Use headings (##, ###) for sections and subsections
   - Use bullet points (- or *) for lists
   - Use numbered lists (1., 2., 3.) for ordered items
   - Put each point on a new line
   - Use line breaks between paragraphs
   - Use `code` formatting for commands, keywords, or technical terms

Example format:
"To delete data from a database, use the **DELETE** command [1].

Alternatively, you can use:
- **TRUNCATE TABLE** to delete all rows [2]
- **DROP TABLE** to delete the entire table [3]"

Rules:
- Answer based strictly on the provided context
- The most relevant chunks are listed first ([1] is most relevant)
- Cite accurately - only reference chunks that contain the information
- If information is not in the context, say so clearly
- Format your response with proper Markdown for readability
- Use line breaks and structure for clarity

User question: {message}"""
        else:
            # No context available
            full_prompt = f"""You are a helpful AI assistant for students.

User question: {message}

Note: No source documents are available. Please provide a general helpful response."""
        
        # 5. Stream response from Gemini
        # Send citations first
        for citation in citations:
            yield {
                "event": "citation",
                "data": citation,
            }
        
        # Stream text chunks from Gemini
        text_received = False
        accumulated_text = ""
        
        try:
            # Use generate_content with the full prompt (simpler and more reliable)
            # Add generation config for better reliability
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 40,
            }
            response = self.model.generate_content(
                full_prompt, 
                stream=True,
                generation_config=generation_config
            )
            
            chunk_count = 0
            for chunk in response:
                chunk_count += 1
                # Check different possible attributes for text
                text = None
                
                # Try direct .text attribute first
                if hasattr(chunk, 'text') and chunk.text:
                    text = chunk.text
                # Try accessing through candidates
                elif hasattr(chunk, 'candidates') and chunk.candidates and len(chunk.candidates) > 0:
                    candidate = chunk.candidates[0]
                    # Check for finish_reason (might indicate blocking)
                    if hasattr(candidate, 'finish_reason'):
                        finish_reason = candidate.finish_reason
                        if finish_reason and finish_reason != 1:  # 1 = STOP, other values indicate issues
                            print(f"[WARNING] Gemini finish_reason: {finish_reason}")
                            if finish_reason == 3:  # SAFETY
                                yield {
                                    "event": "error",
                                    "data": {"error": "Response was blocked by safety filters. Please try rephrasing your question."},
                                }
                                return
                    
                    if hasattr(candidate, 'content') and candidate.content:
                        if hasattr(candidate.content, 'parts') and candidate.content.parts:
                            for part in candidate.content.parts:
                                if hasattr(part, 'text') and part.text:
                                    text = part.text
                                    break
                
                # Additional check: try to get text from the response object itself
                if not text and hasattr(response, 'text'):
                    text = response.text
                
                if text and text.strip():
                    text_received = True
                    accumulated_text += text
                    yield {
                        "event": "chunk",
                        "data": {"text": text},
                    }
            
            # Log if we received chunks but no text
            if chunk_count > 0 and not text_received:
                print(f"[WARNING] Received {chunk_count} chunks but no text content extracted")
        
        except Exception as e:
            import traceback
            error_msg = f"Gemini API error: {type(e).__name__}: {str(e)}"
            print(f"[ERROR] {error_msg}")
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            yield {
                "event": "error",
                "data": {"error": error_msg},
            }
            return
        
        # Check if we received any text before sending done
        if not text_received:
            print(f"[WARNING] No text received from Gemini. Accumulated text length: {len(accumulated_text)}")
            # Try to get the full response if streaming didn't work
            try:
                # Fallback: try non-streaming generation
                generation_config = {
                    "temperature": 0.7,
                    "top_p": 0.8,
                    "top_k": 40,
                }
                fallback_response = self.model.generate_content(
                    full_prompt, 
                    stream=False,
                    generation_config=generation_config
                )
                if hasattr(fallback_response, 'text') and fallback_response.text:
                    text_received = True
                    yield {
                        "event": "chunk",
                        "data": {"text": fallback_response.text},
                    }
                else:
                    yield {
                        "event": "error",
                        "data": {"error": "No response generated. The model may have been blocked or encountered an error. Please try again."},
                    }
                    return
            except Exception as fallback_error:
                print(f"[ERROR] Fallback generation also failed: {fallback_error}")
                yield {
                    "event": "error",
                    "data": {"error": f"Failed to generate response: {str(fallback_error)}"},
                }
                return
        
        # Done
        yield {
            "event": "done",
            "data": {},
        }

