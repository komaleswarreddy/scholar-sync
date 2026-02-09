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
        self.last_retrieval_trace = None  # Store last retrieval trace for debug
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
        # 1. Query retrieval (with Phase 2 agents if enabled)
        filter_dict = {"source_id": {"$in": active_source_ids}} if active_source_ids else None
        
        # Use enhanced retriever with query text and conversation history
        if settings.USE_RETRIEVAL_AGENTS:
            results = await self.retriever.retrieve(
                query=message,
                top_k=settings.TOP_K_CHUNKS,
                filter=filter_dict,
                conversation_history=history,
            )
        else:
            # Fallback to simple retrieval
            query_embedding = await self.embedder.generate_embedding(message)
            results = await self.retriever.retrieve(
                query_embedding=query_embedding,
                top_k=settings.TOP_K_CHUNKS,
                filter=filter_dict,
            )
        
        # Store retrieval trace for debug (if available)
        if settings.RAG_DEBUG and "debug_trace" in results:
            self.last_retrieval_trace = results["debug_trace"]
        
        # 3. Build context from retrieved chunks (already sorted by relevance/score from Pinecone)
        # First, collect unique source_ids to fetch their titles
        unique_source_ids = list(set([match["metadata"]["source_id"] for match in results["matches"]]))
        
        # Fetch source titles from database
        from sqlalchemy import select
        from packages.core.database.models.source import Source
        import uuid as uuid_lib
        
        # Define tenant_uuid outside conditional block so it's always available
        tenant_uuid = uuid_lib.UUID(self.tenant_id)
        
        source_titles_map = {}
        if unique_source_ids:
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
        
        # Also fetch ALL source titles for document-name detection
        all_sources_result = await self.db.execute(
            select(Source.id, Source.title).where(
                Source.tenant_id == tenant_uuid,
                Source.user_id == self.user_id
            )
        )
        all_sources = all_sources_result.all()
        all_source_titles_map = {str(source.id): source.title for source in all_sources}
        
        context_chunks = []
        citations = []
        # Adaptive score threshold: lower for document-name queries, higher for content queries
        # Check if query mentions a document name (check against ALL sources, not just retrieved ones)
        message_lower = message.lower()
        mentioned_documents = []
        for source_id, title in all_source_titles_map.items():
            if not title:
                continue
            title_clean = title.lower().replace(".pdf", "").replace(".txt", "").strip()
            # Check if any significant word from the title appears in the query
            title_words = [w for w in title_clean.split() if len(w) > 2]  # Words longer than 2 chars
            if title_words and any(word in message_lower for word in title_words):
                mentioned_documents.append(title_clean)
                print(f"[RAG] Detected mention of document: '{title}' in query")
        
        # Lower threshold if query mentions a specific document (user asking about a document)
        if mentioned_documents:
            MIN_SCORE_THRESHOLD = 0.30  # Lower threshold for document-name queries
            print(f"[RAG] Detected document-name query. Mentioned documents: {mentioned_documents}. Using lower threshold: {MIN_SCORE_THRESHOLD}")
        else:
            MIN_SCORE_THRESHOLD = 0.45  # Slightly lower than before (was 0.50) for better recall
        
        citation_index = 0
        
        # Track how many chunks we've included from each source
        included_source_ids = {}
        
        for match in results["matches"]:
            chunk_text = match["metadata"]["text"]
            source_id = match["metadata"]["source_id"]
            score = match.get("score", 0)
            source_title = source_titles_map.get(source_id, None)
            
            # Include if score meets threshold
            # OR if it's from a mentioned document and we haven't included enough from it yet
            should_include = False
            if score >= MIN_SCORE_THRESHOLD:
                should_include = True
            elif mentioned_documents and source_title:
                # If query mentions this document, include it even with lower score
                source_title_lower = source_title.lower().replace(".pdf", "").replace(".txt", "").strip()
                if any(mentioned in source_title_lower or source_title_lower in mentioned for mentioned in mentioned_documents):
                    # Include at least top 3 chunks from mentioned document
                    if source_id not in included_source_ids or included_source_ids.get(source_id, 0) < 3:
                        should_include = True
                        print(f"[RAG] Including chunk from mentioned document '{source_title}' (score: {score:.3f})")
            
            if should_include:
                citation_index += 1
                # Note: chunks are numbered [1], [2], etc. in order of relevance (highest score first)
                context_chunks.append(f"[{citation_index}] {chunk_text}")
                citations.append({
                    "source_id": source_id,
                    "chunk_id": match["id"],
                    "text": chunk_text,  # Full text, not preview
                    "score": score,
                    "source_title": source_title,  # Include source title
                })
                # Track how many chunks we've included from each source
                if source_id not in included_source_ids:
                    included_source_ids[source_id] = 0
                included_source_ids[source_id] = included_source_ids.get(source_id, 0) + 1
        
        print(f"[RAG] Filtered citations: {len(citations)} out of {len(results['matches'])} matches (score >= {MIN_SCORE_THRESHOLD})")
        
        # If no citations meet the threshold, include at least the top results to ensure we have context
        if len(citations) == 0 and len(results["matches"]) > 0:
            print(f"[RAG] WARNING: No citations met {MIN_SCORE_THRESHOLD} threshold. Including top results as fallback.")
            # Include top 3 results as fallback
            for i, match in enumerate(results["matches"][:3]):
                chunk_text = match["metadata"]["text"]
                source_id = match["metadata"]["source_id"]
                score = match.get("score", 0)
                source_title = source_titles_map.get(source_id, None)
                citation_index += 1
                context_chunks.append(f"[{citation_index}] {chunk_text}")
                citations.append({
                    "source_id": source_id,
                    "chunk_id": match["id"],
                    "text": chunk_text,
                    "score": score,
                    "source_title": source_title,
                })
        
        context = "\n\n".join(context_chunks)
        
        # CRITICAL SAFEGUARD: Never send empty context to LLM
        if not context or not context.strip():
            print(f"[RAG] CRITICAL: Empty context detected! Citations: {len(citations)}, Context chunks: {len(context_chunks)}")
            print(f"[RAG] Retrieved matches: {len(results.get('matches', []))}")
            
            # Try to get any chunks from results as fallback
            if len(results.get("matches", [])) > 0:
                print(f"[RAG] Applying emergency fallback: using top chunks from results")
                emergency_chunks = []
                emergency_citations = []
                for i, match in enumerate(results["matches"][:6]):  # Top 6
                    chunk_text = match["metadata"]["text"]
                    source_id = match["metadata"]["source_id"]
                    source_title = source_titles_map.get(source_id, None)
                    emergency_chunks.append(f"[{i+1}] {chunk_text}")
                    emergency_citations.append({
                        "source_id": source_id,
                        "chunk_id": match["id"],
                        "text": chunk_text,
                        "score": match.get("score", 0),
                        "source_title": source_title,
                    })
                context = "\n\n".join(emergency_chunks)
                citations = emergency_citations
                print(f"[RAG] Emergency fallback applied: {len(emergency_chunks)} chunks")
            else:
                # Last resort: raise error
                raise ValueError(f"[RAG] CRITICAL: No context available and no fallback chunks found. Cannot generate response.")
        
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
        
        # Track feature usage
        from packages.core.monitoring.metrics import get_metrics_collector
        metrics = get_metrics_collector()
        metrics.record_feature_usage(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            feature="chat",
            endpoint="/chat/stream"
        )
        
        # Get LLM client for chat (Gemini)
        provider, model = get_model_for_task("chat")
        llm_client = get_llm_client(provider=provider, model=model, temperature=0.7)
        
        # Stream text chunks from LLM
        text_received = False
        accumulated_text = ""
        stream_completed = False
        start_time = None
        import time
        
        print(f"[RAG] Starting stream generation. Context chunks: {len(context_chunks)}, Prompt length: {len(full_prompt)} chars")
        
        try:
            start_time = time.time()
            async for chunk in llm_client.stream_generate(
                prompt=full_prompt,
                temperature=0.7,
                max_tokens=settings.CHAT_MAX_TOKENS,  # Set max_tokens to prevent premature cutoff
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                feature_tag="chat"
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
                    # Log finish reason if available
                    finish_reason = chunk.metadata.get("finish_reason") if chunk.metadata else None
                    if finish_reason:
                        print(f"[RAG] Stream completed. Finish reason: {finish_reason}, Total text length: {len(accumulated_text)} chars")
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
        
        # Check if response seems incomplete (ends with incomplete sentence)
        if accumulated_text and len(accumulated_text.strip()) < 50:
            print(f"[WARNING] Response seems very short ({len(accumulated_text)} chars). Full text: {accumulated_text[:200]}")
        
        # Record metrics after stream completes
        if start_time:
            latency_ms = (time.time() - start_time) * 1000
            # Estimate tokens: 1 token ≈ 4 characters
            estimated_prompt_tokens = len(full_prompt) // 4
            estimated_completion_tokens = len(accumulated_text) // 4
            
            # Record metrics if we have reasonable estimates
            if estimated_prompt_tokens > 0 or estimated_completion_tokens > 0:
                from packages.core.guardrails.cost_manager import get_cost_manager
                cost_manager = get_cost_manager()
                try:
                    await cost_manager.record_usage(
                        tenant_id=self.tenant_id,
                        user_id=self.user_id,
                        model=llm_client.model,
                        provider=llm_client.provider.value,
                        prompt_tokens=estimated_prompt_tokens,
                        completion_tokens=estimated_completion_tokens,
                        feature_tag="chat",
                        latency_ms=latency_ms,
                    )
                    print(f"[RAG] Recorded streaming metrics: prompt_tokens={estimated_prompt_tokens}, completion_tokens={estimated_completion_tokens}, latency={latency_ms:.1f}ms")
                except Exception as e:
                    print(f"[WARNING] [RAG] Failed to record streaming metrics: {e}")
        
        # Only send done if we actually received text
        print(f"[RAG] Stream completed successfully. Received {len(accumulated_text)} characters of text. Preview: {accumulated_text[:100]}...")
        
        # Include retrieval trace in done event if debug mode enabled
        done_data = {}
        if settings.RAG_DEBUG and self.last_retrieval_trace:
            done_data["retrieval_trace"] = self.last_retrieval_trace
        
        yield {
            "event": "done",
            "data": done_data,
        }


