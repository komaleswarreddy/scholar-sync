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
        print(f"📊 Step 2: Querying Pinecone (top_k={settings.TOP_K_CHUNKS}, sources={active_source_ids})...")
        filter_dict = {"source_id": {"$in": active_source_ids}} if active_source_ids else None
        results = await self.vector_service.query_vectors(
            query_embedding=query_embedding,
            top_k=settings.TOP_K_CHUNKS,
            filter=filter_dict,
        )
        print(f"✅ Found {len(results.get('matches', []))} matches")
        
        # 3. Build context from retrieved chunks
        context_chunks = []
        citations = []
        for i, match in enumerate(results["matches"], 1):
            chunk_text = match["metadata"]["text"]
            source_id = match["metadata"]["source_id"]
            context_chunks.append(f"[{i}] {chunk_text}")
            citations.append({
                "source_id": source_id,
                "chunk_id": match["id"],
                "text": chunk_text[:200],  # Preview
                "score": match["score"],
            })
        
        context = "\n\n".join(context_chunks)
        
        # 4. Construct prompt with context
        if context:
            # If we have context from sources, include it in the prompt
            full_prompt = f"""You are a helpful AI assistant for students. Answer questions based ONLY on the provided context. Cite sources using [1], [2], etc.

Context:
{context}

Instructions:
- Answer based strictly on the provided context
- If information is not in the context, say so
- Use citations [1], [2], etc. when referencing context
- Be concise and clear

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
        try:
            print(f"📤 Sending prompt to Gemini (length: {len(full_prompt)})")
            # Use generate_content with the full prompt (simpler and more reliable)
            response = self.model.generate_content(full_prompt, stream=True)
            
            chunk_count = 0
            for chunk in response:
                chunk_count += 1
                # Check different possible attributes for text
                text = None
                
                # Try direct .text attribute first
                if hasattr(chunk, 'text') and chunk.text:
                    text = chunk.text
                # Try accessing through candidates
                elif hasattr(chunk, 'candidates') and chunk.candidates:
                    candidate = chunk.candidates[0]
                    if hasattr(candidate, 'content') and candidate.content:
                        if hasattr(candidate.content, 'parts') and candidate.content.parts:
                            for part in candidate.content.parts:
                                if hasattr(part, 'text') and part.text:
                                    text = part.text
                                    break
                
                if text:
                    print(f"📥 Received chunk {chunk_count}: {text[:50]}...")
                    yield {
                        "event": "chunk",
                        "data": {"text": text},
                    }
                else:
                    # Debug: log what we got
                    print(f"⚠️ Chunk {chunk_count} has no text. Type: {type(chunk)}, Attrs: {[a for a in dir(chunk) if not a.startswith('_')]}")
            
            print(f"✅ Streamed {chunk_count} chunks total")
        except Exception as e:
            import traceback
            error_msg = f"Gemini API error: {type(e).__name__}: {str(e)}"
            print(f"❌ {error_msg}")
            print(f"❌ Traceback: {traceback.format_exc()}")
            yield {
                "event": "error",
                "data": {"error": error_msg},
            }
            return
        
        # Done
        yield {
            "event": "done",
            "data": {},
        }

