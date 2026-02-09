"""
Retriever

Handles retrieval of relevant chunks from vector store for RAG pipeline.
Enhanced with Phase 2 retrieval quality agents with guardrails.
"""

from typing import List, Dict, Any, Optional
from config.settings import settings
from packages.core.rag.vectorstores.pinecone_store import PineconeVectorStore
from packages.core.rag.embedder import Embedder
from packages.core.rag.hybrid_retriever import HybridRetriever
from packages.core.rag.agents import (
    IntentClassifier,
    ScopeNarrower,
    QueryRewriter,
    MMRDiversity,
    Reranker,
    ContextSelector,
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
    6. Reranking → Rerank by relevance (guardrails: keep original if weak confidence)
    7. Context Selection → Final filtering (min 6 chunks, token budget, adjacent chunks)
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.vector_store = PineconeVectorStore(tenant_id)
        self.embedder = Embedder(tenant_id)
        
        # Initialize Phase 2 agents if enabled
        if settings.USE_RETRIEVAL_AGENTS:
            self.intent_classifier = IntentClassifier(tenant_id)
            self.scope_narrower = ScopeNarrower(tenant_id)
            self.query_rewriter = QueryRewriter(tenant_id)
            self.hybrid_retriever = HybridRetriever(
                vector_weight=settings.HYBRID_VECTOR_WEIGHT,
                keyword_weight=settings.HYBRID_KEYWORD_WEIGHT
            )
            self.mmr_diversity = MMRDiversity(lambda_param=settings.MMR_LAMBDA)
            self.reranker = Reranker(tenant_id, use_llm=settings.USE_LLM_RERANKING)
            self.context_selector = ContextSelector(
                max_context_chunks=settings.MAX_CONTEXT_CHUNKS,
                min_relevance_score=settings.SIMILARITY_THRESHOLD
            )
        else:
            self.intent_classifier = None
            self.scope_narrower = None
            self.query_rewriter = None
            self.hybrid_retriever = None
            self.mmr_diversity = None
            self.reranker = None
            self.context_selector = None
    
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
    
    async def retrieve(
        self,
        query_embedding: Optional[List[float]] = None,
        query: Optional[str] = None,
        top_k: int = None,
        filter: Optional[Dict] = None,
        conversation_history: Optional[List[Dict]] = None,
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
            if query_embedding is None:
                raise ValueError("query_embedding required when USE_RETRIEVAL_AGENTS is False")
            results = await self.vector_store.query_vectors(
                query_embedding=query_embedding,
                top_k=top_k,
                filter=filter,
            )
            debug_trace["retrieved_chunks_initial"] = {
                "count": len(results.get("matches", [])),
                "ids": [m.get("id") for m in results.get("matches", [])]
            }
            if settings.RAG_DEBUG:
                results["debug_trace"] = debug_trace
            return results
        
        # Phase 2: Enhanced retrieval pipeline
        if query is None:
            raise ValueError("query required when USE_RETRIEVAL_AGENTS is True")
        
        self._log("START", f"Retrieval pipeline started", {"query": query, "top_k": top_k})
        
        # 1. Intent Classification
        intent_result = await self.intent_classifier.classify_intent(
            query=query,
            conversation_history=conversation_history
        )
        intent = intent_result.get("intent")
        intent_confidence = intent_result.get("confidence", 0.5)
        intent_reasoning = intent_result.get("reasoning", "")
        
        debug_trace["detected_intent"] = str(intent) if intent else None
        debug_trace["intent_confidence"] = intent_confidence
        
        self._log("INTENT", f"Intent classified: {intent} (confidence: {intent_confidence:.2f})", {
            "intent": str(intent),
            "confidence": intent_confidence,
            "reasoning": intent_reasoning
        })
        
        # Intent classifier safety: route to default if confidence low
        INTENT_CONFIDENCE_THRESHOLD = 0.5
        if intent_confidence < INTENT_CONFIDENCE_THRESHOLD:
            self._log("INTENT", f"Low confidence ({intent_confidence:.2f}), using default QA pipeline")
            debug_trace["guardrails_applied"].append("low_intent_confidence_fallback")
            # Continue with pipeline but use generic intent
        
        # 2. Scope Narrowing (skip if we expect small document set)
        # We'll check document count after initial retrieval
        scope_result = await self.scope_narrower.narrow_scope(
            query=query,
            conversation_history=conversation_history
        )
        focused_query = scope_result.get("focused_query", query)
        key_terms = scope_result.get("key_terms", [])
        suggested_max_chunks = scope_result.get("max_chunks", top_k)
        
        self._log("SCOPE", f"Scope narrowed", {
            "original": query,
            "focused": focused_query,
            "key_terms": key_terms,
            "suggested_max": suggested_max_chunks
        })
        
        # 3. Query Rewriting (with confidence threshold)
        rewrite_result = await self.query_rewriter.rewrite_query(
            query=focused_query,
            conversation_history=conversation_history,
            max_rewrites=2,
            confidence_threshold=settings.QUERY_REWRITE_CONFIDENCE_THRESHOLD
        )
        rewritten_queries = rewrite_result.get("queries", [focused_query])
        rewrite_confidence = rewrite_result.get("confidence", 0.0)
        used_rewrites = rewrite_result.get("used_rewrites", False)
        
        debug_trace["rewritten_queries"] = rewritten_queries
        debug_trace["rewrite_confidence"] = rewrite_confidence
        
        self._log("REWRITE", f"Query rewritten", {
            "original": focused_query,
            "rewritten": rewritten_queries,
            "confidence": rewrite_confidence,
            "used_rewrites": used_rewrites
        })
        
        # Use primary query (first in list, which is always original)
        primary_query = rewritten_queries[0] if rewritten_queries else focused_query
        
        # 4. Generate embedding for primary query
        if query_embedding is None:
            query_embedding = await self.embedder.generate_embedding(primary_query)
        
        # 5. Hybrid Retrieval (Vector + Keyword)
        # Retrieve more chunks initially to have buffer for filtering
        initial_retrieval_k = max(top_k * 3, 20)  # Get at least 20 chunks for filtering
        
        # Store original query embedding for fallback
        original_query_embedding = query_embedding
        
        # Perform vector search first with primary query
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
            for rewritten_query in rewritten_queries[1:]:  # Skip original (already searched)
                try:
                    rewritten_embedding = await self.embedder.generate_embedding(rewritten_query)
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
        
        debug_trace["after_mmr"] = {"count": len(diverse_matches)}
        
        # 7. Reranking - Rerank by relevance to query (with guardrails)
        # Safeguard: Reranker must always keep at least top 6 chunks
        if len(diverse_matches) <= 1:
            reranked_matches = diverse_matches
            reranker_confidence = 1.0  # Perfect confidence if only one chunk
        else:
            reranked_result = await self.reranker.rerank(
                chunks=diverse_matches,
                query=primary_query,
                top_k=None  # Don't limit here, let context selector handle it
            )
            # Handle both dict and list return formats (backward compatibility)
            if isinstance(reranked_result, dict):
                reranked_matches = reranked_result.get("chunks", diverse_matches)
                reranker_confidence = reranked_result.get("confidence", 0.5)
            else:
                # Legacy format (list)
                reranked_matches = reranked_result
                reranker_confidence = 0.7  # Default confidence for legacy
            
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
                print(f"[RAG_PIPELINE] GUARDRAIL: Reranker returned {len(reranked_matches)} chunks, enforcing minimum {min_chunks_after_rerank}")
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
        selected_matches = self.context_selector.select_context(
            retrieved_chunks=reranked_matches,
            query=primary_query,
            max_tokens=settings.CONTEXT_TOKEN_BUDGET,
            min_chunks=settings.MIN_CONTEXT_CHUNKS
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
