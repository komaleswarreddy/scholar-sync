"""
RAG Service

Handles Retrieval-Augmented Generation for chat.
Uses LLM abstraction layer and prompt templates.
"""

from typing import List, Dict, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
import re

from config.settings import settings
from packages.core.security import RefusalReason
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
        
        # Phase 4: Session Memory & Caching
        if settings.USE_SESSION_MEMORY:
            from packages.core.memory import AnswerCache, ChatSummarizer, MemoryManager
            
            if settings.ENABLE_ANSWER_CACHE:
                self.answer_cache = AnswerCache(
                    cache_dir=f"cache/answers/{tenant_id}",
                    default_ttl_seconds=settings.ANSWER_CACHE_TTL_SECONDS,
                    max_cache_size=1000
                )
            else:
                self.answer_cache = None
            
            if settings.ENABLE_CHAT_SUMMARIZATION:
                self.chat_summarizer = ChatSummarizer(
                    recent_window=settings.CHAT_KEEP_RECENT,
                    summarize_after=settings.CHAT_SUMMARIZE_AFTER,
                    max_summary_length=500
                )
            else:
                self.chat_summarizer = None
            
            if settings.ENABLE_MEMORY_PRUNING:
                self.memory_manager = MemoryManager(
                    max_history_messages=settings.MAX_HISTORY_MESSAGES,
                    max_history_tokens=settings.MAX_HISTORY_TOKENS,
                    keep_recent=settings.CHAT_KEEP_RECENT,
                    prune_strategy=settings.MEMORY_PRUNING_STRATEGY
                )
            else:
                self.memory_manager = None
        else:
            self.answer_cache = None
            self.chat_summarizer = None
            self.memory_manager = None
        
        # Phase 5: Security & Student Guardrails
        if settings.USE_SECURITY_GUARDRAILS:
            from packages.core.security import (
                SafetyFilter, RefusalTemplates, PromptInjectionDetector,
                IntentGate, PIIDetector, RestrictedRetriever
            )
            
            if settings.ENABLE_SAFETY_FILTERS:
                self.safety_filter = SafetyFilter(
                    strict_mode=settings.SAFETY_STRICT_MODE,
                    block_threshold=0.7
                )
            else:
                self.safety_filter = None
            
            if settings.ENABLE_REFUSAL_TEMPLATES:
                self.refusal_templates = RefusalTemplates()
            else:
                self.refusal_templates = None
            
            if settings.ENABLE_INJECTION_DETECTION:
                self.injection_detector = PromptInjectionDetector(
                    strict_mode=settings.SAFETY_STRICT_MODE,
                    detection_threshold=settings.INJECTION_DETECTION_THRESHOLD
                )
            else:
                self.injection_detector = None
            
            if settings.ENABLE_INTENT_GATE:
                self.intent_gate = IntentGate(
                    strict_mode=settings.SAFETY_STRICT_MODE,
                    academic_threshold=settings.INTENT_ACADEMIC_THRESHOLD
                )
            else:
                self.intent_gate = None
            
            if settings.ENABLE_PII_DETECTION:
                self.pii_detector = PIIDetector(redact_mode=True)
            else:
                self.pii_detector = None
            
            # Syllabus-locked RAG: wrap retriever if enabled
            if settings.ENABLE_SYLLABUS_LOCK and settings.APPROVED_SOURCE_IDS:
                approved_sources = [
                    s.strip() for s in settings.APPROVED_SOURCE_IDS.split(",")
                    if s.strip()
                ]
                if approved_sources:
                    self.retriever = RestrictedRetriever(
                        base_retriever=self.retriever,
                        approved_source_ids=approved_sources,
                        strict_mode=settings.SAFETY_STRICT_MODE
                    )
        else:
            self.safety_filter = None
            self.refusal_templates = None
            self.injection_detector = None
            self.intent_gate = None
            self.pii_detector = None
    
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
        # Phase 5: PII Detection - Detect and redact PII in input
        if self.pii_detector and settings.ENABLE_PII_DETECTION:
            redacted_message, pii_info = self.pii_detector.redact(message)
            if pii_info["has_pii"]:
                print(f"[SECURITY] PII detected in input: {pii_info['pii_types']} - redacted")
                if self.refusal_templates:
                    refusal_msg = self.refusal_templates.get_refusal(
                        RefusalReason.PII_DETECTED
                    )
                    yield {
                        "event": "error",
                        "data": {"error": refusal_msg}
                    }
                    return
                message = redacted_message  # Use redacted version
        
        # Phase 5: Prompt Injection Detection
        if self.injection_detector and settings.ENABLE_INJECTION_DETECTION:
            injection_check = self.injection_detector.detect(message)
            if injection_check["is_injection"]:
                print(f"[SECURITY] Prompt injection detected: {injection_check['injection_types']}")
                if self.refusal_templates:
                    refusal_msg = self.refusal_templates.get_refusal(
                        RefusalReason.PROMPT_INJECTION
                    )
                    yield {
                        "event": "error",
                        "data": {"error": refusal_msg}
                    }
                    return
        
        # Phase 5: Intent Gate - Academic-only enforcement
        if self.intent_gate and settings.ENABLE_INTENT_GATE:
            intent_check = self.intent_gate.check_and_block(message)
            if intent_check["blocked"]:
                print(f"[SECURITY] Non-academic intent blocked: {intent_check['intent_category']}")
                yield {
                    "event": "error",
                    "data": {"error": intent_check["message"]}
                }
                return
        
        # Phase 5: Safety Filter - Input moderation
        if self.safety_filter and settings.ENABLE_SAFETY_FILTERS:
            safety_check = self.safety_filter.check_input(message, context="academic")
            if safety_check["blocked"]:
                print(f"[SECURITY] Unsafe input blocked: {safety_check['categories']}")
                if self.refusal_templates:
                    refusal_msg = self.refusal_templates.get_refusal(
                        RefusalReason.SAFETY_VIOLATION
                    )
                    yield {
                        "event": "error",
                        "data": {"error": refusal_msg}
                    }
                    return
        
        # Phase 4: Answer Caching - Check cache first
        if self.answer_cache and settings.ENABLE_ANSWER_CACHE:
            cached_answer = self.answer_cache.get(message, active_source_ids, self.tenant_id)
            if cached_answer:
                print(f"[RAG] Cache HIT for query: {message[:50]}...")
                # Return cached answer
                for citation in cached_answer.get("citations", []):
                    yield {
                        "event": "citation",
                        "data": citation,
                    }
                
                # Stream cached answer (simulate streaming)
                answer_text = cached_answer["answer"]
                # Split into chunks for streaming
                chunk_size = 50
                for i in range(0, len(answer_text), chunk_size):
                    chunk = answer_text[i:i+chunk_size]
                    yield {
                        "event": "chunk",
                        "data": {"text": chunk},
                    }
                
                yield {
                    "event": "done",
                    "data": {"cached": True, "timestamp": cached_answer.get("timestamp")},
                }
                return
        
        # Phase 4: Memory Pruning - Prune history if needed
        if self.memory_manager and settings.ENABLE_MEMORY_PRUNING:
            prune_result = self.memory_manager.prune_history(history, message)
            if prune_result["removed_count"] > 0:
                history = prune_result["pruned_history"]
                print(f"[RAG] Memory pruned: {prune_result['original_count']} → {prune_result['new_count']} messages ({prune_result['strategy_used']})")
        
        # Phase 4: Chat Summarization - Summarize if needed
        if self.chat_summarizer and settings.ENABLE_CHAT_SUMMARIZATION:
            if self.chat_summarizer.should_summarize(history):
                # Use simple summarization (fast, no LLM cost)
                summary_result = self.chat_summarizer.summarize_history(history, message)
                if summary_result["was_summarized"]:
                    history = summary_result["summarized_history"]
                    print(f"[RAG] History summarized: {summary_result['original_count']} → {summary_result['new_count']} messages")
        
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
        
        # Track total context tokens for optimization
        total_context_tokens = 0
        max_chunk_length = getattr(settings, 'MAX_CHUNK_LENGTH', 500)
        use_compression = getattr(settings, 'USE_CHUNK_COMPRESSION', True)
        
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
                
                # INPUT TOKEN OPTIMIZATION: Truncate chunk text if too long
                original_chunk_length = len(chunk_text)
                if len(chunk_text) > max_chunk_length:
                    # Truncate at sentence boundary if possible
                    truncated = chunk_text[:max_chunk_length]
                    last_period = truncated.rfind('.')
                    last_question = truncated.rfind('?')
                    last_exclamation = truncated.rfind('!')
                    last_sentence_end = max(last_period, last_question, last_exclamation)
                    
                    if last_sentence_end > max_chunk_length * 0.7:  # If sentence end is reasonably close
                        chunk_text = chunk_text[:last_sentence_end + 1]
                    else:
                        # Truncate at word boundary
                        last_space = truncated.rfind(' ')
                        if last_space > max_chunk_length * 0.8:
                            chunk_text = chunk_text[:last_space] + "..."
                        else:
                            chunk_text = truncated + "..."
                    
                    print(f"[RAG] Truncated chunk {citation_index}: {original_chunk_length} → {len(chunk_text)} chars")
                
                # INPUT TOKEN OPTIMIZATION: Compress lower-scoring chunks
                if use_compression and citation_index > 4 and score < 0.7:
                    # For chunks beyond top 4 with lower scores, compress to first 300 chars + key sentences
                    if len(chunk_text) > 300:
                        # Keep first 300 chars and try to extract key sentences
                        first_part = chunk_text[:300]
                        remaining = chunk_text[300:]
                        # Extract first complete sentence from remaining if available
                        sentences = re.split(r'([.!?]+)', remaining)
                        if len(sentences) >= 2:
                            first_sentence = sentences[0] + sentences[1] if len(sentences) > 1 else ""
                            if len(first_sentence) < 200:
                                chunk_text = first_part + " " + first_sentence + "..."
                            else:
                                chunk_text = first_part + "..."
                        else:
                            chunk_text = first_part + "..."
                        print(f"[RAG] Compressed chunk {citation_index} (score: {score:.2f}): {original_chunk_length} → {len(chunk_text)} chars")
                
                # Note: chunks are numbered [1], [2], etc. in order of relevance (highest score first)
                context_chunks.append(f"[{citation_index}] {chunk_text}")
                
                # Store full text in citations (for display), but use truncated in context
                citations.append({
                    "source_id": source_id,
                    "chunk_id": match["id"],
                    "text": match["metadata"]["text"],  # Full text for citations
                    "score": score,
                    "source_title": source_title,
                })
                
                # Track tokens (rough estimate: 1 token ≈ 4 characters)
                chunk_tokens = len(chunk_text) // 4
                total_context_tokens += chunk_tokens
                
                # Track how many chunks we've included from each source
                if source_id not in included_source_ids:
                    included_source_ids[source_id] = 0
                included_source_ids[source_id] = included_source_ids.get(source_id, 0) + 1
        
        print(f"[RAG] Filtered citations: {len(citations)} out of {len(results['matches'])} matches (score >= {MIN_SCORE_THRESHOLD})")
        print(f"[RAG] Total context tokens (estimated): ~{total_context_tokens} tokens from {len(context_chunks)} chunks")
        
        # If no citations meet the threshold, include at least the top results to ensure we have context
        if len(citations) == 0 and len(results["matches"]) > 0:
            print(f"[RAG] WARNING: No citations met {MIN_SCORE_THRESHOLD} threshold. Including top results as fallback.")
            # Include top 3 results as fallback
            for i, match in enumerate(results["matches"][:3]):
                chunk_text = match["metadata"]["text"]
                source_id = match["metadata"]["source_id"]
                score = match.get("score", 0)
                source_title = source_titles_map.get(source_id, None)
                
                # Truncate fallback chunks too
                if len(chunk_text) > max_chunk_length:
                    truncated = chunk_text[:max_chunk_length]
                    last_period = truncated.rfind('.')
                    if last_period > max_chunk_length * 0.7:
                        chunk_text = chunk_text[:last_period + 1]
                    else:
                        chunk_text = truncated + "..."
                
                citation_index += 1
                context_chunks.append(f"[{citation_index}] {chunk_text}")
                citations.append({
                    "source_id": source_id,
                    "chunk_id": match["id"],
                    "text": match["metadata"]["text"],  # Full text for citations
                    "score": score,
                    "source_title": source_title,
                })
                total_context_tokens += len(chunk_text) // 4
        
        context = "\n\n".join(context_chunks)
        
        # Log final context size
        final_context_tokens = len(context) // 4  # Rough estimate
        print(f"[RAG] Final context size: {len(context)} chars (~{final_context_tokens} tokens)")
        
        # INPUT TOKEN OPTIMIZATION: Further compress if still too large
        max_context_tokens = settings.CONTEXT_TOKEN_BUDGET
        if final_context_tokens > max_context_tokens * 1.2:  # 20% over budget
            print(f"[RAG] WARNING: Context exceeds budget ({final_context_tokens} > {max_context_tokens}). Compressing...")
            # Compress by truncating lower-priority chunks
            compressed_chunks = []
            remaining_budget = max_context_tokens
            for i, chunk in enumerate(context_chunks):
                chunk_tokens = len(chunk) // 4
                if i < 3:  # Keep top 3 chunks full
                    compressed_chunks.append(chunk)
                    remaining_budget -= chunk_tokens
                else:
                    # Compress remaining chunks more aggressively
                    if remaining_budget > 200:  # Reserve 200 tokens for prompt
                        # Truncate to fit remaining budget
                        max_chunk_chars = min(len(chunk), (remaining_budget - 200) // (len(context_chunks) - i) * 4)
                        if len(chunk) > max_chunk_chars:
                            truncated = chunk[:max_chunk_chars]
                            last_period = truncated.rfind('.')
                            if last_period > max_chunk_chars * 0.7:
                                chunk = chunk[:last_period + 1]
                            else:
                                chunk = truncated + "..."
                        compressed_chunks.append(chunk)
                        remaining_budget -= len(chunk) // 4
                    else:
                        # Skip remaining chunks if budget exhausted
                        print(f"[RAG] Skipping {len(context_chunks) - i} chunks due to token budget")
                        break
            
            context = "\n\n".join(compressed_chunks)
            final_context_tokens = len(context) // 4
            print(f"[RAG] Compressed context: {final_context_tokens} tokens")
        
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
        
        # Initialize Phase 3 output optimization agents
        early_stop_detector = None
        output_formatter = None
        output_length_limiter = None
        citation_enforcer = None
        
        if settings.USE_OUTPUT_OPTIMIZATION:
            from packages.core.rag.agents import (
                EarlyStopDetector,
                OutputFormatter,
                OutputFormat,
                OutputLengthLimiter,
                CitationEnforcer,
            )
            
            if settings.USE_EARLY_STOP:
                early_stop_detector = EarlyStopDetector(
                    enabled=True,
                    min_length=50
                )
            
            # Initialize output formatter with default format
            format_map = {
                "bullet_points": OutputFormat.BULLET_POINTS,
                "numbered_list": OutputFormat.NUMBERED_LIST,
                "paragraph": OutputFormat.PARAGRAPH,
                "structured": OutputFormat.STRUCTURED,
            }
            default_format = format_map.get(settings.DEFAULT_OUTPUT_FORMAT, OutputFormat.BULLET_POINTS)
            output_formatter = OutputFormatter(
                default_format=default_format,
                use_headings=True,
                max_items=10
            )
            
            # Initialize output length limiter
            max_tokens = settings.MAX_OUTPUT_TOKENS or settings.CHAT_MAX_TOKENS
            output_length_limiter = OutputLengthLimiter(
                max_tokens=max_tokens,
                max_characters=settings.MAX_OUTPUT_CHARACTERS,
                max_sentences=settings.MAX_OUTPUT_SENTENCES,
                hard_limit=True
            )
            
            # Initialize citation enforcer
            if settings.ENFORCE_CITATIONS:
                citation_enforcer = CitationEnforcer(strict_mode=True)
        
        # Stream text chunks from LLM
        text_received = False
        accumulated_text = ""
        stream_completed = False
        start_time = None
        early_stopped = False
        import time
        
        print(f"[RAG] Starting stream generation. Context chunks: {len(context_chunks)}, Prompt length: {len(full_prompt)} chars")
        if settings.USE_OUTPUT_OPTIMIZATION:
            print(f"[RAG] Phase 3 optimizations enabled: early_stop={settings.USE_EARLY_STOP}, format={settings.DEFAULT_OUTPUT_FORMAT}, enforce_citations={settings.ENFORCE_CITATIONS}")
        
        try:
            start_time = time.time()
            last_chunk_content = ""
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
                    chunk_content = chunk.content
                    accumulated_text += chunk_content
                    last_chunk_content = chunk_content
                    
                    # Yield chunk first
                    yield {
                        "event": "chunk",
                        "data": {"text": chunk_content},
                    }
                    
                    # Phase 3: Early stop detection (during streaming) - check after yielding
                    if early_stop_detector and settings.USE_EARLY_STOP:
                        stop_result = early_stop_detector.should_stop(
                            accumulated_text=accumulated_text,
                            query=message,
                            last_chunk=chunk_content
                        )
                        if stop_result["should_stop"]:
                            print(f"[RAG] Early stop triggered: {stop_result['reason']} (confidence: {stop_result['confidence']:.2f})")
                            early_stopped = True
                            # Find best stop point at sentence boundary
                            stop_point = early_stop_detector.find_stop_point(accumulated_text)
                            if stop_point and stop_point < len(accumulated_text):
                                # Truncate accumulated text to stop point
                                accumulated_text = accumulated_text[:stop_point]
                                print(f"[RAG] Truncated to {stop_point} characters at sentence boundary")
                            # Break to stop streaming
                            break
                
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
        
        # Phase 3: Post-processing validation and logging
        if settings.USE_OUTPUT_OPTIMIZATION and accumulated_text:
            original_length = len(accumulated_text)
            
            # 1. Output length validation (logging only - max_tokens enforced by LLM)
            if output_length_limiter:
                length_check = output_length_limiter.check_length(accumulated_text)
                if length_check["exceeds_limits"]:
                    print(f"[RAG] WARNING: Output exceeds limits: {', '.join(length_check['warnings'])}")
                    print(f"[RAG] Length stats: {length_check['char_count']} chars, ~{length_check['token_estimate']} tokens, {length_check['sentence_count']} sentences")
                else:
                    print(f"[RAG] Output length OK: {length_check['char_count']} chars, ~{length_check['token_estimate']} tokens, {length_check['sentence_count']} sentences")
            
            # 2. Output format validation (check if bullet points are used)
            if output_formatter and settings.DEFAULT_OUTPUT_FORMAT == "bullet_points":
                # Check if response uses bullet points
                has_bullets = bool(re.search(r'^[\-\*\+]\s+', accumulated_text, re.MULTILINE))
                if not has_bullets and len(accumulated_text) > 100:
                    print(f"[RAG] WARNING: Response not in bullet point format (preferred format)")
            
            # 3. Citation validation and enforcement check
            if citation_enforcer and settings.ENFORCE_CITATIONS:
                try:
                    citation_check = citation_enforcer.check_citations(accumulated_text, citations)
                    if citation_check["needs_fix"]:
                        print(f"[RAG] WARNING: {len(citation_check['uncited_claims'])} uncited claims detected")
                        print(f"[RAG] Citation coverage: {citation_check['citation_count']} citations found")
                        # Log uncited claims for monitoring
                        if citation_check['uncited_claims']:
                            print(f"[RAG] Sample uncited claims: {citation_check['uncited_claims'][:2]}")
                    else:
                        print(f"[RAG] Citation check passed: {citation_check['citation_count']} citations found")
                except Exception as e:
                    print(f"[WARNING] [RAG] Citation validation failed: {e}")
        
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
        if early_stopped:
            print(f"[RAG] Early stop was applied to prevent verbose response")
        
        # Phase 5: Safety Filter - Output moderation
        if self.safety_filter and settings.ENABLE_SAFETY_FILTERS and accumulated_text:
            output_safety = self.safety_filter.check_output(accumulated_text, context="academic")
            if output_safety["blocked"]:
                print(f"[SECURITY] Unsafe output blocked: {output_safety['categories']}")
                if self.refusal_templates:
                    accumulated_text = self.refusal_templates.get_refusal(
                        RefusalReason.SAFETY_VIOLATION
                    )
                else:
                    accumulated_text = "I can't provide that information. How can I help with your studies?"
        
        # Phase 5: PII Detection - Redact PII from output
        if self.pii_detector and settings.ENABLE_PII_DETECTION and accumulated_text:
            redacted_output, pii_info = self.pii_detector.redact(accumulated_text)
            if pii_info["has_pii"]:
                print(f"[SECURITY] PII detected in output: {pii_info['pii_types']} - redacted")
                accumulated_text = redacted_output
        
        # Phase 4: Answer Caching - Cache the answer
        if self.answer_cache and settings.ENABLE_ANSWER_CACHE and accumulated_text:
            try:
                self.answer_cache.set(
                    query=message,
                    source_ids=active_source_ids,
                    answer=accumulated_text,
                    citations=citations,
                    tenant_id=self.tenant_id,
                    ttl_seconds=settings.ANSWER_CACHE_TTL_SECONDS
                )
                print(f"[RAG] Answer cached for future queries")
            except Exception as e:
                print(f"[WARNING] Failed to cache answer: {e}")
        
        # Include retrieval trace in done event if debug mode enabled
        done_data = {}
        if settings.RAG_DEBUG and self.last_retrieval_trace:
            done_data["retrieval_trace"] = self.last_retrieval_trace
        
        yield {
            "event": "done",
            "data": done_data,
        }


