"""
Retriever

Handles retrieval of relevant chunks from vector store for RAG pipeline.
Enhanced with Phase 2 retrieval quality agents with guardrails.
"""

from typing import List, Dict, Any, Optional
import asyncio
import re
import time

from packages.core.monitoring.pipeline_trace import trace_async, trace_snippet, record_retrieval_span
from config.settings import settings
from packages.core.rag.vectorstores.pinecone_store import PineconeVectorStore
from packages.core.rag.embedder import Embedder
from packages.core.rag.hybrid_retriever import HybridRetriever
from packages.core.rag.llama_adapters import LlamaIndexRetrievalAdapter
from packages.core.rag.agents import (
    IntentClassifier,
    QueryRewriter,
    MMRDiversity,
    ContextSelector,
    UserIntent,
    QueryComplexityScorer,
)
from packages.core.rag.metadata_query import (
    extra_retrieval_variants,
    is_metadata_attribution_query,
)


class Retriever:
    """
    Service for retrieving relevant chunks from vector store.
    
    Enhanced with Phase 2 retrieval quality agents with guardrails:
    1. Intent Classification → Classify user intent (with confidence check)
    2. Scope Narrowing → Narrow retrieval scope (skip if small doc set)
    3. Query Rewriting → Generate query variants (preserve semantic intent)
    4. Hybrid Retrieval → Vector + keyword search (normalized scores)
    5. MMR Diversity → Select diverse chunks (skip if < 8 chunks, preserve high relevance)
    6. Reranking → Cohere Rerank API only (requires COHERE_API_KEY; no LLM/keyword fallback)
    7. Context Selection → Final filtering (min 6 chunks, token budget, adjacent chunks)
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.vector_store = PineconeVectorStore(tenant_id)
        self.embedder = Embedder(tenant_id)
        self.li_retriever = (
            LlamaIndexRetrievalAdapter(tenant_id)
            if getattr(settings, "USE_LLAMA_INDEX_RAG", False)
            else None
        )
        # Store previous chunks for conversation-aware retrieval
        self.previous_chunks = []

        # Cohere-only reranking (shared by simple + Phase 2 retrieval paths)
        self.cohere_reranker = None
        if getattr(settings, "COHERE_API_KEY", ""):
            try:
                from packages.core.rag.rerank.cohere_reranker import CohereReranker

                self.cohere_reranker = CohereReranker()
            except Exception:
                self.cohere_reranker = None

        # Initialize Phase 2 agents if enabled
        if settings.USE_RETRIEVAL_AGENTS:
            self.intent_classifier = IntentClassifier(tenant_id)
            self.query_rewriter = QueryRewriter(tenant_id)
            self.complexity_scorer = QueryComplexityScorer()
            self.hybrid_retriever = HybridRetriever(
                vector_weight=settings.HYBRID_VECTOR_WEIGHT,
                keyword_weight=settings.HYBRID_KEYWORD_WEIGHT
            )
            self.mmr_diversity = MMRDiversity(lambda_param=settings.MMR_LAMBDA)
            self.context_selector = ContextSelector(
                max_context_chunks=settings.MAX_CONTEXT_CHUNKS,
                min_relevance_score=settings.SIMILARITY_THRESHOLD
            )
        else:
            self.intent_classifier = None
            self.query_rewriter = None
            self.complexity_scorer = None
            self.hybrid_retriever = None
            self.mmr_diversity = None
            self.context_selector = None
        
        # Initialize retrieval cache for query rewrites and reranks
        from packages.core.memory.retrieval_cache import RetrievalCache
        self.retrieval_cache = RetrievalCache(
            cache_dir=f"cache/retrieval/{tenant_id}",
            default_ttl_seconds=3600,
            max_cache_size=500
        )
    
    def _log(self, stage: str, message: str, data: Optional[Dict] = None):
        """Log debug information if RAG_DEBUG is enabled."""
        if settings.RAG_DEBUG:
            log_msg = f"[RAG_DEBUG] [{stage}] {message}"
            if data:
                import json
                log_msg += f" | Data: {json.dumps(data, default=str)}"
            print(log_msg)
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation: 1 token ≈ 4 characters."""
        return len(text) // 4

    async def _cohere_rerank_chunks(
        self, query: str, chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Rerank via Cohere only. Missing key or errors → keep vector ordering."""
        if not query or not chunks or len(chunks) <= 1 or self.cohere_reranker is None:
            return chunks
        try:
            return await asyncio.to_thread(
                lambda: self.cohere_reranker.rerank(
                    query=query,
                    matches=chunks,
                    top_n=len(chunks),
                )
            )
        except Exception as e:
            print(f"[RAG_PIPELINE] Cohere rerank failed: {e}")
            return sorted(chunks, key=lambda x: x.get("score", 0), reverse=True)

    def get_context_size(self, intent: Optional[UserIntent] = None) -> int:
        """
        Get context size (top_k) based on intent.
        
        Args:
            intent: User intent from classification
            
        Returns:
            Suggested top_k value
        """
        if intent is None:
            return settings.TOP_K_CHUNKS
        
        # Intent-based context sizing (SUMMARY needs broad retrieval — was incorrectly 3 chunks)
        intent_sizing = {
            UserIntent.SUMMARY: getattr(
                settings, "DOCUMENT_SUMMARY_RETRIEVAL_TOP_K", max(settings.TOP_K_CHUNKS * 6, 48)
            ),
            UserIntent.WHOLE_DOCUMENT_SUMMARY: getattr(
                settings, "DOCUMENT_SUMMARY_RETRIEVAL_TOP_K", max(settings.TOP_K_CHUNKS * 6, 48)
            ),
            UserIntent.DEFINITION: 8,  # Definitions often need surrounding context, not a single line
            UserIntent.QUESTION: 14,
            UserIntent.EXPLANATION: 12,
            UserIntent.HOW_TO: 12,
            UserIntent.COMPARISON: 14,
            UserIntent.ANALYSIS: 16,
            UserIntent.CREATION: 12,
            UserIntent.GENERAL: 12,
        }
        
        return intent_sizing.get(intent, settings.TOP_K_CHUNKS)
    
    def is_follow_up_query(self, query: str) -> bool:
        """
        Detect if query is a follow-up that should reuse previous chunks.
        
        Args:
            query: User query text
            
        Returns:
            True if query is a follow-up
        """
        follow_up_patterns = [
            r'\bexplain\s+more\b',
            r'\bcontinue\b',
            r'\belaborate\b',
            r'\bwhy\b',
            r'\bhow\s+exactly\b',
            r'\btell\s+me\s+more\b',
            r'\bgo\s+deeper\b',
            r'\bexpand\b',
            r'\bmore\s+details?\b',
        ]
        
        query_lower = query.lower()
        for pattern in follow_up_patterns:
            if re.search(pattern, query_lower):
                return True
        return False
    
    async def retrieve(
        self,
        query_embedding: Optional[List[float]] = None,
        query: Optional[str] = None,
        top_k: int = None,
        filter: Optional[Dict] = None,
        conversation_history: Optional[List[Dict]] = None,
        classified_intent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve relevant chunks from vector store.
        
        Enhanced with Phase 2 agents if enabled, with guardrails to prevent over-filtering.
        
        Args:
            query_embedding: Query vector embedding (optional if query provided)
            query: Query text (required if Phase 2 agents enabled)
            top_k: Number of results (defaults to settings.TOP_K_CHUNKS)
            filter: Optional metadata filter
            conversation_history: Optional conversation history for context
            
        Returns:
            Query results with matches and metadata (intent, etc.)
        """
        # Check if this is a follow-up query that should reuse previous chunks
        is_follow_up = False
        if query:
            is_follow_up = self.is_follow_up_query(query)
        previous_chunk_ids = {chunk.get("id") for chunk in self.previous_chunks} if self.previous_chunks else set()
        
        # Use intent-based context sizing if intent is available
        # We'll get intent first, then adjust top_k
        if top_k is None and settings.USE_RETRIEVAL_AGENTS and query:
            # We'll set top_k after intent classification
            top_k = settings.TOP_K_CHUNKS  # Temporary default
        else:
            top_k = top_k or settings.TOP_K_CHUNKS
        
        # Initialize debug trace
        debug_trace = {
            "original_query": query,
            "detected_intent": None,
            "intent_confidence": None,
            "rewritten_queries": [],
            "rewrite_confidence": None,
            "retrieved_chunks_initial": {"count": 0, "ids": []},
            "after_hybrid_merge": {"count": 0},
            "after_scope_filter": {"count": 0},
            "after_mmr": {"count": 0},
            "after_rerank": {"count": 0, "scores": []},
            "final_chunks_sent_to_llm": {"count": 0, "token_size": 0},
            "guardrails_applied": []
        }
        
        # If Phase 2 agents disabled, use simple retrieval
        if not settings.USE_RETRIEVAL_AGENTS:
            # Allow query-only callers; generate embedding here.
            if query_embedding is None:
                if not query:
                    raise ValueError(
                        "query or query_embedding required when USE_RETRIEVAL_AGENTS is False"
                    )
                query_embedding = await trace_async(
                    "Retrieval/simple_embedding",
                    self.embedder.generate_embedding(query),
                    input_summary={"query_preview": trace_snippet(query, 240)},
                    output_fn=lambda emb: {"embedding_dims": len(emb) if emb else 0},
                    feature_tag="embedding",
                )

            async def _simple_retrieve():
                if self.li_retriever is not None and query:
                    active_source_ids = None
                    if filter and isinstance(filter, dict):
                        active_source_ids = (
                            filter.get("source_id", {}).get("$in", None)
                            if isinstance(filter.get("source_id", {}), dict)
                            else None
                        )
                    return await self.li_retriever.retrieve(
                        query=query,
                        top_k=top_k,
                        active_source_ids=active_source_ids,
                    )
                return await self.vector_store.query_vectors(
                    query_embedding=query_embedding,
                    top_k=top_k,
                    filter=filter,
                )

            results = await trace_async(
                "Retrieval/simple_vector_query",
                _simple_retrieve(),
                input_summary={"top_k": top_k, "path": "llama" if self.li_retriever is not None else "pinecone"},
                output_fn=lambda r: {"match_count": len((r or {}).get("matches") or [])},
            )
            matches = results.get("matches", []) or []
            if query and matches:
                matches = await trace_async(
                    "Retrieval/simple_cohere_rerank",
                    self._cohere_rerank_chunks(query, matches),
                    input_summary={"chunks_in": len(matches)},
                    output_fn=lambda m: {"chunks_out": len(m) if m else 0},
                    feature_tag="cohere_rerank",
                )
                results["matches"] = matches
            debug_trace["retrieved_chunks_initial"] = {
                "count": len(matches),
                "ids": [m.get("id") for m in matches]
            }
            if settings.RAG_DEBUG:
                results["debug_trace"] = debug_trace
            # Metadata for downstream (e.g. chat generator prompt) — simple path has no scope/rewrite
            results["focused_query"] = query
            results["rewritten_queries"] = [query]
            return results
        
        # Phase 2: Enhanced retrieval pipeline
        if query is None:
            raise ValueError("query required when USE_RETRIEVAL_AGENTS is True")
        
        self._log("START", f"Retrieval pipeline started", {"query": query, "top_k": top_k})
        
        # 0. Query Complexity Scoring (rerank / confidence only; rewrite always runs)
        complexity_result = self.complexity_scorer.score_complexity(query)
        should_skip_rerank = complexity_result.get("should_skip_rerank", False)
        should_skip_confidence = complexity_result.get("should_skip_confidence", False)
        
        debug_trace["query_complexity"] = str(complexity_result.get("complexity"))
        debug_trace["word_count"] = complexity_result.get("word_count")
        debug_trace["has_operators"] = complexity_result.get("has_operators")
        
        if should_skip_rerank or should_skip_confidence:
            self._log("COMPLEXITY", f"Simple query detected - skipping some expensive operations", {
                "complexity": complexity_result.get("complexity"),
                "skip_rerank": should_skip_rerank,
                "skip_confidence": should_skip_confidence
            })
            debug_trace["guardrails_applied"].append("simple_query_skip_expensive_ops")
        
        # 1. Intent — reuse the classified intent from the LangGraph IntentClassify node
        #    (no second LLM call). Fall back to local classification only when caller
        #    does not provide a pre-classified intent (e.g. tests, CLI).
        from packages.core.rag.agents import UserIntent
        intent = None
        intent_confidence = 0.8
        if classified_intent:
            _intent_map = {v.value: v for v in UserIntent}
            intent = _intent_map.get(classified_intent, UserIntent.QUESTION)
            self._log("INTENT", f"Reusing pre-classified intent: {intent}")
        else:
            intent_result = await self.intent_classifier.classify_intent(
                query=query,
                conversation_history=conversation_history,
            )
            intent = intent_result.get("intent")
            intent_confidence = intent_result.get("confidence", 0.5)
        
        debug_trace["detected_intent"] = str(intent) if intent else None
        debug_trace["intent_confidence"] = intent_confidence
        
        # Set top_k based on intent (replace fixed TOP_K_CHUNKS)
        top_k = self.get_context_size(intent)
        debug_trace["intent_based_top_k"] = top_k
        self._log("INTENT", f"Using intent-based top_k: {top_k} (intent: {intent})")
        
        # Conversation-aware retrieval: if follow-up query, reuse previous chunks + add 2-3 new
        if is_follow_up and self.previous_chunks:
            # For follow-ups, only retrieve 2-3 new chunks
            new_chunks_to_retrieve = 3
            self._log("CONVERSATION", f"Follow-up query detected. Reusing {len(self.previous_chunks)} previous chunks, retrieving {new_chunks_to_retrieve} new chunks")
            debug_trace["conversation_aware"] = True
            debug_trace["previous_chunks_count"] = len(self.previous_chunks)
            debug_trace["new_chunks_to_retrieve"] = new_chunks_to_retrieve
            # We'll merge previous chunks with new ones later
            top_k = new_chunks_to_retrieve  # Only retrieve a few new chunks
        
        # 2. Query Rewriting — resolves coreferences, produces optimized retrieval queries
        focused_query = query
        key_terms: list = []
        rewritten_queries = [query]
        rewrite_confidence = 1.0
        used_rewrites = False

        source_ids_list = list(filter.get("source_id", {}).get("$in", [])) if filter else None
        cached_rewrite = self.retrieval_cache.get_rewrite(query, source_ids_list)

        if cached_rewrite:
            rewritten_queries = cached_rewrite
            rewrite_confidence = 1.0
            used_rewrites = True
            self._log("CACHE", f"Using cached query rewrite", {"rewritten_queries": rewritten_queries})
            debug_trace["rewrite_cache_hit"] = True
        else:
            rewrite_result = await trace_async(
                "Retrieval/query_rewrite",
                self.query_rewriter.rewrite_query(
                    query=query,
                    conversation_history=conversation_history,
                    max_rewrites=2,
                    confidence_threshold=settings.QUERY_REWRITE_CONFIDENCE_THRESHOLD,
                ),
                input_summary={"raw_query": trace_snippet(query, 240)},
                output_fn=lambda r: {
                    "rewritten_queries": [trace_snippet(x, 160) for x in (r or {}).get("queries", [])[:4]],
                    "confidence": (r or {}).get("confidence"),
                },
                feature_tag="query_rewriter",
            )
            rewritten_queries = rewrite_result.get("queries", [query])
            rewrite_confidence = rewrite_result.get("confidence", 0.0)
            used_rewrites = rewrite_result.get("used_rewrites", False)

            if used_rewrites and rewritten_queries:
                self.retrieval_cache.set_rewrite(query, rewritten_queries, source_ids_list)
                debug_trace["rewrite_cache_miss"] = True
        
        focused_query = rewritten_queries[0] if rewritten_queries else query
        debug_trace["rewritten_queries"] = rewritten_queries
        debug_trace["rewrite_confidence"] = rewrite_confidence
        
        self._log("REWRITE", f"Query rewritten", {
            "original": query,
            "rewritten": rewritten_queries,
            "confidence": rewrite_confidence,
            "used_rewrites": used_rewrites
        })

        if is_metadata_attribution_query(query) or is_metadata_attribution_query(focused_query):
            seen_lower = {str(x).strip().lower() for x in rewritten_queries if x}
            for v in extra_retrieval_variants(focused_query):
                vl = v.strip().lower()
                if vl and vl not in seen_lower:
                    rewritten_queries.append(v)
                    seen_lower.add(vl)
            debug_trace["guardrails_applied"].append("metadata_query_variants")
        
        primary_query = rewritten_queries[0] if rewritten_queries else query
        
        # 4. Generate embedding for primary query
        if query_embedding is None:
            query_embedding = await trace_async(
                "Retrieval/embedding",
                self.embedder.generate_embedding(primary_query),
                input_summary={"query": trace_snippet(primary_query, 240)},
                output_fn=lambda emb: {"dimensions": len(emb) if emb else 0},
                feature_tag="embedding",
            )
        
        # 5. Hybrid Retrieval (Vector + Keyword)
        # Retrieve more chunks initially to have buffer for filtering
        initial_retrieval_k = max(top_k * 3, 20)  # Get at least 20 chunks for filtering
        
        # Store original query embedding for fallback
        original_query_embedding = query_embedding
        
        _vh_t0 = time.perf_counter()
        # Perform vector search first with primary query
        if self.li_retriever is not None:
            active_source_ids = None
            if filter and isinstance(filter, dict):
                active_source_ids = (
                    filter.get("source_id", {}).get("$in", None)
                    if isinstance(filter.get("source_id", {}), dict)
                    else None
                )
            vector_results = await self.li_retriever.retrieve(
                query=primary_query,
                top_k=initial_retrieval_k,
                active_source_ids=active_source_ids,
            )
        else:
            vector_results = await self.vector_store.query_vectors(
                query_embedding=query_embedding,
                top_k=initial_retrieval_k,
                filter=filter,
            )
        vector_matches = vector_results.get("matches", [])
        
        debug_trace["retrieved_chunks_initial"] = {
            "count": len(vector_matches),
            "ids": [m.get("id") for m in vector_matches[:10]]  # First 10 IDs
        }
        
        print(f"[RAG_PIPELINE] Stage: RETRIEVE | Chunks: {len(vector_matches)}")
        self._log("RETRIEVAL", f"Initial vector retrieval", {
            "count": len(vector_matches),
            "top_k_requested": initial_retrieval_k
        })
        
        # Combine with keyword search using hybrid retriever (normalized scores)
        hybrid_matches = self.hybrid_retriever.combine_results(
            vector_results=vector_matches,
            query=primary_query,
        )
        record_retrieval_span(
            "Retrieval/retrieve",
            (time.perf_counter() - _vh_t0) * 1000,
            input_summary={
                "query": trace_snippet(primary_query, 200),
                "top_k": initial_retrieval_k,
            },
            output_summary={
                "vector_chunks": len(vector_matches),
                "after_hybrid_merge": len(hybrid_matches),
            },
        )
        
        debug_trace["after_hybrid_merge"] = {"count": len(hybrid_matches)}
        print(f"[RAG_PIPELINE] Stage: HYBRID | Chunks: {len(hybrid_matches)}")
        
        self._log("HYBRID", f"Hybrid retrieval completed", {
            "vector_count": len(vector_matches),
            "hybrid_count": len(hybrid_matches),
            "vector_weight": settings.HYBRID_VECTOR_WEIGHT,
            "keyword_weight": settings.HYBRID_KEYWORD_WEIGHT
        })
        
        # If we have rewritten queries with confidence, also search with them
        # But compare results and fallback to original if rewritten performs worse
        original_hybrid_count = len(hybrid_matches)
        if used_rewrites and len(rewritten_queries) > 1:
            additional_matches = []
            for rewritten_query in rewritten_queries[1:]:  # Additional variants (primary already searched)
                try:
                    rewritten_embedding = await self.embedder.generate_embedding(rewritten_query)
                    if self.li_retriever is not None:
                        active_source_ids = None
                        if filter and isinstance(filter, dict):
                            active_source_ids = (
                                filter.get("source_id", {}).get("$in", None)
                                if isinstance(filter.get("source_id", {}), dict)
                                else None
                            )
                        rewritten_results = await self.li_retriever.retrieve(
                            query=rewritten_query,
                            top_k=initial_retrieval_k // 2,
                            active_source_ids=active_source_ids,
                        )
                    else:
                        rewritten_results = await self.vector_store.query_vectors(
                            query_embedding=rewritten_embedding,
                            top_k=initial_retrieval_k // 2,  # Get fewer for variants
                            filter=filter,
                        )
                    variant_matches = rewritten_results.get("matches", [])
                    # Combine with keyword search
                    variant_hybrid = self.hybrid_retriever.combine_results(
                        vector_results=variant_matches,
                        query=rewritten_query,
                    )
                    additional_matches.extend(variant_hybrid)
                except Exception as e:
                    self._log("REWRITE", f"Error searching with rewritten query: {e}")
                    continue
            
            # Merge results, avoiding duplicates, keeping best scores
            seen_ids = {}
            for match in hybrid_matches:
                chunk_id = match.get("id")
                if chunk_id:
                    seen_ids[chunk_id] = match
            
            for match in additional_matches:
                chunk_id = match.get("id")
                if chunk_id:
                    # Keep the match with higher score
                    if chunk_id not in seen_ids or match.get("score", 0) > seen_ids[chunk_id].get("score", 0):
                        seen_ids[chunk_id] = match
            
            merged_hybrid_matches = list(seen_ids.values())
            # Re-sort by score
            merged_hybrid_matches.sort(key=lambda x: x.get("score", 0), reverse=True)
            
            # Safeguard: If rewritten query retrieves fewer chunks, use original
            if len(merged_hybrid_matches) < original_hybrid_count:
                print(f"[RAG_PIPELINE] WARNING: Rewritten query retrieved fewer chunks ({len(merged_hybrid_matches)} < {original_hybrid_count}). Using original query results.")
                self._log("REWRITE", f"Rewritten query performed worse, using original", {
                    "rewritten_count": len(merged_hybrid_matches),
                    "original_count": original_hybrid_count
                })
                debug_trace["guardrails_applied"].append("rewritten_query_fallback_to_original")
                # Keep original hybrid_matches
            else:
                hybrid_matches = merged_hybrid_matches
                print(f"[RAG_PIPELINE] Rewritten query improved results: {len(hybrid_matches)} chunks (was {original_hybrid_count})")
        
        # Check document chunk count to decide if we should skip MMR/scope narrowing
        # Safeguard: Disable MMR and scope narrowing if document has < 40 chunks
        total_chunks_available = len(hybrid_matches)
        skip_mmr = total_chunks_available < 8  # Skip MMR if < 8 chunks
        skip_scope_narrowing = total_chunks_available < 40  # Skip scope narrowing if < 40 chunks
        
        if skip_scope_narrowing:
            debug_trace["guardrails_applied"].append("skip_scope_narrowing_small_doc_set")
            print(f"[RAG_PIPELINE] GUARDRAIL: Skipping scope narrowing (small doc set: {total_chunks_available} < 40 chunks)")
            self._log("GUARDRAIL", f"Skipping scope narrowing (small doc set: {total_chunks_available} chunks)")
        
        if skip_mmr:
            debug_trace["guardrails_applied"].append("skip_mmr_small_doc_set")
            print(f"[RAG_PIPELINE] GUARDRAIL: Skipping MMR diversity (small doc set: {total_chunks_available} < 8 chunks)")
            self._log("GUARDRAIL", f"Skipping MMR diversity (small doc set: {total_chunks_available} chunks)")
        
        # 6. MMR Diversity - Select diverse chunks (skip if small doc set)
        _mmr_t0 = time.perf_counter()
        if skip_mmr or len(hybrid_matches) <= top_k:
            diverse_matches = hybrid_matches
            print(f"[RAG_PIPELINE] Stage: MMR | Chunks: {len(diverse_matches)} (skipped)")
            self._log("MMR", f"Skipped MMR (small doc set or already <= top_k)")
        else:
            # Extract embeddings for MMR (if available in metadata)
            # Note: Pinecone may not return embeddings by default, so we'll use scores
            diverse_matches = self.mmr_diversity.select_diverse_chunks(
                chunks=hybrid_matches,
                query_embedding=query_embedding,
                top_k=min(top_k * 2, len(hybrid_matches))  # Get more for reranking
            )
            print(f"[RAG_PIPELINE] Stage: MMR | Chunks: {len(diverse_matches)} (from {len(hybrid_matches)})")
            self._log("MMR", f"MMR diversity applied", {
                "input_count": len(hybrid_matches),
                "output_count": len(diverse_matches),
                "lambda": settings.MMR_LAMBDA
            })
        record_retrieval_span(
            "Retrieval/mmr",
            (time.perf_counter() - _mmr_t0) * 1000,
            input_summary={"chunks_in": len(hybrid_matches), "skipped": skip_mmr},
            output_summary={"chunks_out": len(diverse_matches)},
        )
        
        debug_trace["after_mmr"] = {"count": len(diverse_matches)}
        
        # 7. Reranking - Rerank by relevance to query (with guardrails) - Skip for simple queries
        # Safeguard: Rerank stage must always keep at least top 6 chunks
        if len(diverse_matches) <= 1:
            reranked_matches = diverse_matches
            reranker_confidence = 1.0  # Perfect confidence if only one chunk
            record_retrieval_span(
                "Retrieval/cohere_rerank",
                0.0,
                input_summary={"chunks_in": len(diverse_matches), "skipped": False, "reason": "single_chunk"},
                output_summary={"chunks_out": len(reranked_matches)},
                feature_tag="cohere_rerank",
            )
        elif should_skip_rerank:
            # Skip reranking for simple queries
            reranked_matches = diverse_matches
            reranker_confidence = 0.8  # Default confidence for simple queries
            self._log("RERANK", f"Skipping reranking (simple query)")
            debug_trace["rerank_skipped"] = True
            record_retrieval_span(
                "Retrieval/cohere_rerank",
                0.0,
                input_summary={"chunks_in": len(diverse_matches), "skipped": True, "reason": "simple_query"},
                output_summary={"chunks_out": len(reranked_matches)},
                feature_tag="cohere_rerank",
            )
        else:
            # Check cache first
            source_ids_list = list(filter.get("source_id", {}).get("$in", [])) if filter else None
            cached_rerank = self.retrieval_cache.get_rerank(primary_query, source_ids_list)
            
            if cached_rerank:
                reranked_matches = cached_rerank
                reranker_confidence = 0.9  # High confidence for cached results
                self._log("CACHE", f"Using cached reranked chunks", {"chunk_count": len(reranked_matches)})
                debug_trace["rerank_cache_hit"] = True
                record_retrieval_span(
                    "Retrieval/cohere_rerank",
                    0.0,
                    input_summary={"chunks_in": len(diverse_matches), "cache_hit": True},
                    output_summary={"chunks_out": len(reranked_matches)},
                    feature_tag="cohere_rerank",
                )
            elif self.cohere_reranker is not None:
                try:
                    reranked_matches = await trace_async(
                        "Retrieval/cohere_rerank",
                        asyncio.to_thread(
                            lambda: self.cohere_reranker.rerank(
                                query=primary_query,
                                matches=diverse_matches,
                                top_n=len(diverse_matches),
                            )
                        ),
                        input_summary={"chunks_in": len(diverse_matches), "query": trace_snippet(primary_query, 120)},
                        output_fn=lambda m: {"chunks_out": len(m) if m else 0},
                        feature_tag="cohere_rerank",
                    )
                    reranker_confidence = 0.92
                except Exception as e:
                    print(f"[RAG_PIPELINE] Cohere rerank failed: {e}")
                    reranked_matches = sorted(
                        diverse_matches, key=lambda x: x.get("score", 0), reverse=True
                    )
                    reranker_confidence = 0.55
                if reranked_matches:
                    self.retrieval_cache.set_rerank(primary_query, reranked_matches, source_ids_list)
                    debug_trace["rerank_cache_miss"] = True
            else:
                print("[RAG_PIPELINE] COHERE_API_KEY not set; skipping rerank (no LLM/keyword fallback)")
                reranked_matches = list(diverse_matches)
                reranker_confidence = 0.82
                record_retrieval_span(
                    "Retrieval/cohere_rerank",
                    0.0,
                    input_summary={"chunks_in": len(diverse_matches), "skipped": True, "reason": "cohere_missing"},
                    output_summary={"chunks_out": len(reranked_matches)},
                    feature_tag="cohere_rerank",
                )
            
            # Guardrail: if reranker confidence weak, keep original vector order
            RERANKER_CONFIDENCE_THRESHOLD = 0.6
            if reranker_confidence < RERANKER_CONFIDENCE_THRESHOLD:
                print(f"[RAG_PIPELINE] GUARDRAIL: Low reranker confidence ({reranker_confidence:.2f}), keeping original order")
                self._log("RERANK", f"Low reranker confidence ({reranker_confidence:.2f}), keeping original order")
                debug_trace["guardrails_applied"].append("low_reranker_confidence_keep_original")
                # Keep original order (by score)
                reranked_matches = sorted(diverse_matches, key=lambda x: x.get("score", 0), reverse=True)
            
            # Safeguard: Ensure we never drop below top 6 chunks after rerank
            min_chunks_after_rerank = max(settings.MIN_CONTEXT_CHUNKS, min(len(diverse_matches), top_k))
            if len(reranked_matches) < min_chunks_after_rerank:
                print(f"[RAG_PIPELINE] GUARDRAIL: Rerank returned {len(reranked_matches)} chunks, enforcing minimum {min_chunks_after_rerank}")
                # Add back top chunks by original score
                original_sorted = sorted(diverse_matches, key=lambda x: x.get("score", 0), reverse=True)
                reranked_ids = {m.get("id") for m in reranked_matches}
                for chunk in original_sorted:
                    if chunk.get("id") not in reranked_ids and len(reranked_matches) < min_chunks_after_rerank:
                        reranked_matches.append(chunk)
                reranked_matches = reranked_matches[:min_chunks_after_rerank]
                self._log("RERANK", f"Added chunks to meet minimum ({min_chunks_after_rerank})")
                debug_trace["guardrails_applied"].append("min_chunks_after_rerank_enforced")
        
        # Extract scores for debug
        rerank_scores = [m.get("score", 0) for m in reranked_matches[:10]]
        debug_trace["after_rerank"] = {
            "count": len(reranked_matches),
            "scores": rerank_scores
        }
        
        print(f"[RAG_PIPELINE] Stage: RERANK | Chunks: {len(reranked_matches)} (from {len(diverse_matches)})")
        self._log("RERANK", f"Reranking completed", {
            "input_count": len(diverse_matches),
            "output_count": len(reranked_matches),
            "confidence": reranker_confidence if 'reranker_confidence' in locals() else 1.0
        })
        
        # 8. Context Selection - Final filtering (with guardrails)
        ctx_budget = settings.CONTEXT_TOKEN_BUDGET
        min_ctx = settings.MIN_CONTEXT_CHUNKS
        max_ctx_chunks = settings.MAX_CONTEXT_CHUNKS
        if intent == UserIntent.SUMMARY:
            ctx_budget = getattr(settings, "DOCUMENT_SUMMARY_CONTEXT_TOKEN_BUDGET", ctx_budget)
            min_ctx = max(
                settings.MIN_CONTEXT_CHUNKS,
                getattr(settings, "DOCUMENT_SUMMARY_MIN_CHUNKS", min_ctx),
            )
            max_ctx_chunks = getattr(settings, "DOCUMENT_SUMMARY_MAX_CONTEXT_CHUNKS", max_ctx_chunks)

        _ctx_t0 = time.perf_counter()
        selected_matches = self.context_selector.select_context(
            retrieved_chunks=reranked_matches,
            query=primary_query,
            max_tokens=ctx_budget,
            min_chunks=min_ctx,
            max_chunks=max_ctx_chunks,
        )
        record_retrieval_span(
            "Retrieval/context_selector",
            (time.perf_counter() - _ctx_t0) * 1000,
            input_summary={"chunks_in": len(reranked_matches), "token_budget": ctx_budget},
            output_summary={"chunks_out": len(selected_matches)},
            feature_tag="context_selector",
        )
        
        # Calculate final token size
        final_token_size = sum(
            self._estimate_tokens(m.get("metadata", {}).get("text", ""))
            for m in selected_matches
        )
        
        print(f"[RAG_PIPELINE] Stage: FINAL_PACK | Chunks: {len(selected_matches)} (from {len(reranked_matches)})")
        
        debug_trace["final_chunks_sent_to_llm"] = {
            "count": len(selected_matches),
            "token_size": final_token_size,
            "chunk_ids": [m.get("id") for m in selected_matches]
        }
        
        self._log("CONTEXT", f"Context selection completed", {
            "input_count": len(reranked_matches),
            "final_count": len(selected_matches),
            "token_size": final_token_size,
            "min_chunks": settings.MIN_CONTEXT_CHUNKS,
            "max_chunks": settings.MAX_CONTEXT_CHUNKS
        })
        
        # Conversation-aware retrieval: Merge previous chunks with new ones for follow-up queries
        if is_follow_up and self.previous_chunks:
            # Filter out chunks that are already in previous_chunks
            new_chunk_ids = {m.get("id") for m in selected_matches}
            previous_chunk_ids = {chunk.get("id") for chunk in self.previous_chunks}
            
            # Only keep new chunks (not in previous)
            truly_new_chunks = [m for m in selected_matches if m.get("id") not in previous_chunk_ids]
            
            # Merge: previous chunks + new chunks (limit new to 2-3)
            merged_chunks = list(self.previous_chunks) + truly_new_chunks[:3]
            
            print(f"[RAG_PIPELINE] CONVERSATION-AWARE: Merged {len(self.previous_chunks)} previous + {len(truly_new_chunks[:3])} new chunks = {len(merged_chunks)} total")
            self._log("CONVERSATION", f"Merged previous and new chunks", {
                "previous_count": len(self.previous_chunks),
                "new_count": len(truly_new_chunks[:3]),
                "total_count": len(merged_chunks)
            })
            
            selected_matches = merged_chunks
            debug_trace["conversation_merged"] = True
            debug_trace["merged_chunks_count"] = len(merged_chunks)
        
        # Update previous_chunks for next query
        self.previous_chunks = selected_matches[:10]  # Keep last 10 chunks for next query
        
        # CRITICAL SAFEGUARD: If final_chunks == 0, use top chunks as fallback
        if len(selected_matches) == 0:
            fallback_count = max(settings.MIN_CONTEXT_CHUNKS, 4)  # At least 4 chunks
            print(f"[RAG_PIPELINE] CRITICAL: Final chunks is 0! Applying fallback: using top {fallback_count} vector chunks")
            self._log("FALLBACK", f"Final chunks is 0, using top {fallback_count} vector chunks as fallback")
            debug_trace["guardrails_applied"].append("empty_context_fallback_to_vector")
            
            # Fallback to top chunks from original retrieval
            if len(vector_matches) > 0:
                # Use top chunks by score
                fallback_matches = sorted(vector_matches, key=lambda x: x.get("score", 0), reverse=True)[:fallback_count]
                selected_matches = fallback_matches
                print(f"[RAG_PIPELINE] Fallback applied: Using {len(selected_matches)} vector chunks")
            elif len(hybrid_matches) > 0:
                # If no vector matches, use hybrid matches
                fallback_matches = sorted(hybrid_matches, key=lambda x: x.get("score", 0), reverse=True)[:fallback_count]
                selected_matches = fallback_matches
                print(f"[RAG_PIPELINE] Fallback applied: Using {len(selected_matches)} hybrid chunks")
            else:
                # Last resort: use any available chunks
                all_available = reranked_matches or diverse_matches or hybrid_matches or vector_matches
                if all_available:
                    selected_matches = all_available[:fallback_count]
                    print(f"[RAG_PIPELINE] Fallback applied: Using {len(selected_matches)} chunks from available pool")
                else:
                    print(f"[RAG_PIPELINE] ERROR: No chunks available for fallback!")
        
        # Ensure we have at least minimum chunks (but respect token budget)
        if len(selected_matches) < settings.MIN_CONTEXT_CHUNKS and len(reranked_matches) >= settings.MIN_CONTEXT_CHUNKS:
            # Calculate current token usage
            current_tokens = sum(
                self._estimate_tokens(m.get("metadata", {}).get("text", ""))
                for m in selected_matches
            )
            remaining_budget = settings.CONTEXT_TOKEN_BUDGET - current_tokens
            
            print(f"[RAG_PIPELINE] GUARDRAIL: Only {len(selected_matches)} chunks selected, adding more to meet minimum {settings.MIN_CONTEXT_CHUNKS}")
            # Add more chunks from reranked to meet minimum, but respect token budget
            selected_ids = {m.get("id") for m in selected_matches}
            for chunk in reranked_matches:
                if chunk.get("id") not in selected_ids and len(selected_matches) < settings.MIN_CONTEXT_CHUNKS:
                    chunk_tokens = self._estimate_tokens(chunk.get("metadata", {}).get("text", ""))
                    # Only add if we have budget (reserve 20% for prompt overhead)
                    if current_tokens + chunk_tokens <= settings.CONTEXT_TOKEN_BUDGET * 0.8:
                        selected_matches.append(chunk)
                        current_tokens += chunk_tokens
                    else:
                        # Truncate chunk to fit budget
                        max_chunk_chars = (remaining_budget - 100) * 4  # Reserve 100 tokens
                        chunk_text = chunk.get("metadata", {}).get("text", "")
                        if len(chunk_text) > max_chunk_chars:
                            truncated = chunk_text[:max_chunk_chars]
                            last_period = truncated.rfind('.')
                            if last_period > max_chunk_chars * 0.7:
                                chunk_text = chunk_text[:last_period + 1]
                            else:
                                chunk_text = truncated + "..."
                            # Update chunk metadata with truncated text
                            chunk_copy = dict(chunk)
                            chunk_copy["metadata"] = dict(chunk.get("metadata", {}))
                            chunk_copy["metadata"]["text"] = chunk_text
                            selected_matches.append(chunk_copy)
                            current_tokens += self._estimate_tokens(chunk_text)
                        else:
                            selected_matches.append(chunk)
                            current_tokens += chunk_tokens
            debug_trace["guardrails_applied"].append("min_context_chunks_enforced")
        
        # Final check: Never send empty context
        if len(selected_matches) == 0:
            raise ValueError(f"[RAG_PIPELINE] CRITICAL ERROR: Cannot proceed with empty context. No chunks available after all fallbacks.")
        
        print(f"[RAG_PIPELINE] FINAL: {len(selected_matches)} chunks ready for LLM (token_size: {final_token_size})")
        
        # Return results in expected format
        result = {
            "matches": selected_matches,
            "intent": intent,
            "intent_confidence": intent_confidence,
            "key_terms": key_terms,
            "focused_query": focused_query,
            "rewritten_queries": rewritten_queries,
            "metadata": {
                "total_retrieved": len(hybrid_matches),
                "after_mmr": len(diverse_matches),
                "after_reranking": len(reranked_matches),
                "final_selected": len(selected_matches),
            }
        }
        
        # Add debug trace if enabled
        if settings.RAG_DEBUG:
            result["debug_trace"] = debug_trace
        
        return result
