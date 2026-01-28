"""
RAG Service

Handles Retrieval-Augmented Generation for chat.
Uses LLM abstraction layer and prompt templates.
"""

from typing import List, Dict, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from packages.core.llm import get_llm_client, get_model_for_task
from packages.core.prompts import load_prompt
from packages.core.rag.vectorstores.pinecone_store import PineconeVectorStore
from packages.core.rag.embedder import Embedder
from packages.core.rag.retriever import Retriever


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
        self.embedder = Embedder(tenant_id)
        self.retriever = Retriever(tenant_id)
    
    async def stream_chat(
        self,
        message: str,
        history: List[Dict],  # List of ChatMessage dicts
        active_source_ids: List[str],
    ) -> AsyncGenerator[Dict, None]:
        """
        Stream chat response with RAG.
        
        Yields:
            Dictionary with 'event' and 'data' keys for SSE
        """
        # 1. Embed query
        query_embedding = await self.embedder.generate_embedding(message)
        
        # 2. Query Pinecone (with tenant namespace and source filter)
        filter_dict = {"source_id": {"$in": active_source_ids}} if active_source_ids else None
        results = await self.retriever.retrieve(
            query_embedding=query_embedding,
            top_k=settings.TOP_K_CHUNKS,
            filter=filter_dict,
        )
        
        # 3. Build context from retrieved chunks (already sorted by relevance/score from Pinecone)
        # First, collect unique source_ids to fetch their titles
        unique_source_ids = list(set([match["metadata"]["source_id"] for match in results["matches"]]))
        
        # Fetch source titles from database
        from sqlalchemy import select
        from packages.core.database.models.source import Source
        import uuid as uuid_lib
        
        source_titles_map = {}
        if unique_source_ids:
            tenant_uuid = uuid_lib.UUID(self.tenant_id)
            source_uuids = [uuid_lib.UUID(sid) for sid in unique_source_ids]
            result = await self.db.execute(
                select(Source.id, Source.title).where(
                    Source.id.in_(source_uuids),
                    Source.tenant_id == tenant_uuid,
                    Source.user_id == self.user_id
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
        
        # 4. Construct prompt using template
        try:
            full_prompt = load_prompt(
                "chat/rag_prompt.j2",
                context=context or "",
                message=message
            )
        except FileNotFoundError:
            # Fallback to inline prompt if template missing
            if context:
                full_prompt = f"""You are a helpful AI assistant for students. Answer questions based ONLY on the provided context.

Context (chunks numbered [1], [2], [3]... in order of relevance - [1] is most relevant):
{context}

User question: {message}"""
            else:
                full_prompt = f"""You are a helpful AI assistant for students.

User question: {message}

Note: No source documents are available. Please provide a general helpful response."""
        
        # 5. Stream response using LLM abstraction
        # Send citations first
        for citation in citations:
            yield {
                "event": "citation",
                "data": citation,
            }
        
        # Get LLM client for chat (Gemini)
        provider, model = get_model_for_task("chat")
        llm_client = get_llm_client(provider=provider, model=model, temperature=0.7)
        
        # Stream text chunks from LLM
        text_received = False
        accumulated_text = ""
        stream_completed = False
        
        try:
            async for chunk in llm_client.stream_generate(
                prompt=full_prompt,
                temperature=0.7
            ):
                # Check for errors in metadata first (before processing content)
                if chunk.metadata and chunk.metadata.get("finish_reason"):
                    finish_reason = chunk.metadata["finish_reason"]
                    if finish_reason == "SAFETY" or finish_reason == 3:
                        print(f"[WARNING] Response blocked by safety filters. Finish reason: {finish_reason}")
                        yield {
                            "event": "error",
                            "data": {"error": "Response was blocked by safety filters. Please try rephrasing your question."},
                        }
                        return
                    # Check for other blocking reasons
                    if finish_reason in ["RECITATION", "OTHER"]:
                        print(f"[WARNING] Response blocked. Finish reason: {finish_reason}")
                        yield {
                            "event": "error",
                            "data": {"error": "Response was blocked. Please try rephrasing your question."},
                        }
                        return
                
                # Process content if available
                if chunk.content and chunk.content.strip():
                    text_received = True
                    accumulated_text += chunk.content
                    yield {
                        "event": "chunk",
                        "data": {"text": chunk.content},
                    }
                
                # Check if stream is done
                if chunk.done:
                    stream_completed = True
                    break
        
        except Exception as e:
            import traceback
            error_msg = f"LLM API error: {type(e).__name__}: {str(e)}"
            print(f"[ERROR] {error_msg}")
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            yield {
                "event": "error",
                "data": {"error": error_msg},
            }
            return
        
        # CRITICAL: Check if we received any text before sending done
        # Use both the flag and accumulated text length for safety
        if not text_received or (accumulated_text and accumulated_text.strip() == ""):
            print(f"[WARNING] No text received from LLM. text_received={text_received}, accumulated_text_length={len(accumulated_text)}, stream_completed={stream_completed}")
            yield {
                "event": "error",
                "data": {"error": "No response generated. The model may have been blocked or encountered an error. Please try again."},
            }
            return
        
        # Only send done if we actually received text
        print(f"[DEBUG] Stream completed successfully. Received {len(accumulated_text)} characters of text.")
        yield {
            "event": "done",
            "data": {},
        }


