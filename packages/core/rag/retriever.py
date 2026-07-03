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
from packages.core.rag.bm25_fusion import LocalBM25, rrf_fuse
from packages.core.rag.llama_adapters import LlamaIndexRetrievalAdapter
from packages.core.rag.agents import (
    IntentClassifier,
    QueryRewriter,
    ScopeNarrower,
    MMRDiversity,
    ContextSelector,
    UserIntent,
    QueryComplexityScorer,
    QueryDecomposer,
)
from packages.core.rag.metadata_query import (
    extra_retrieval_variants,
    extra_factual_retrieval_variants,
    is_factual_recall_query,
    is_metadata_attribution_query,
)
from packages.core.rag.context_aware_weighting import apply_context_aware_scores
from packages.core.rag.retrieval_strategy import resolve_retrieval_strategy
from packages.core.services.ncert_constants import METRICS_TENANT_NCERT


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
    
    def __init__(self, tenant_id: str, user_id: Optional[str] = None):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.vector_store = PineconeVectorStore(tenant_id)
        self.embedder = Embedder(tenant_id, user_id=user_id)
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

        # Hybrid scoring is also used when NCERT global results are merged into
        # non-agent retrieval, so keep it available for both paths.
        self.hybrid_retriever = HybridRetriever(
            vector_weight=settings.HYBRID_VECTOR_WEIGHT,
            keyword_weight=settings.HYBRID_KEYWORD_WEIGHT
        )

        # Initialize Phase 2 agents if enabled
        if settings.USE_RETRIEVAL_AGENTS:
            self.intent_classifier = IntentClassifier(tenant_id, user_id=user_id)
            self.scope_narrower = ScopeNarrower(tenant_id)
            self.query_rewriter = QueryRewriter(tenant_id, user_id=user_id)
            self.query_decomposer = QueryDecomposer(tenant_id, user_id=user_id)
            self.complexity_scorer = QueryComplexityScorer()
            self.mmr_diversity = MMRDiversity(lambda_param=settings.MMR_LAMBDA)
            self.context_selector = ContextSelector(
                max_context_chunks=settings.MAX_CONTEXT_CHUNKS,
                min_relevance_score=settings.SIMILARITY_THRESHOLD
            )
        else:
            self.intent_classifier = None
            self.scope_narrower = None
            self.query_rewriter = None
            self.query_decomposer = None
            self.complexity_scorer = None
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
        
        intent_sizing = {
            UserIntent.SUMMARY: getattr(settings, "DOCUMENT_SUMMARY_RETRIEVAL_TOP_K", 3),
            UserIntent.WHOLE_DOCUMENT_SUMMARY: getattr(
                settings, "DOCUMENT_SUMMARY_RETRIEVAL_TOP_K", 3
            ),
            UserIntent.DEFINITION: 5,
            UserIntent.QUESTION: 7,
            UserIntent.EXPLANATION: 10,
            UserIntent.HOW_TO: 10,
            UserIntent.COMPARISON: 12,
            UserIntent.ANALYSIS: 12,
            UserIntent.CREATION: 10,
            UserIntent.GENERAL: 7,
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

    def _build_retrieval_cache_scope(
        self,
        *,
        include_ncert_global: bool,
        ncert_class: Optional[int],
        ncert_subject: Optional[str],
        ncert_chapter_no: Optional[int],
        ncert_chapter_name: Optional[str],
        ncert_concept: Optional[str] = None,
    ) -> str:
        subject = (str(ncert_subject or "").strip().lower() or "all")
        class_part = str(int(ncert_class)) if ncert_class is not None else "all"
        chapter_no = str(int(ncert_chapter_no)) if ncert_chapter_no is not None else "all"
        chapter_name = (str(ncert_chapter_name or "").strip().lower() or "all")
        concept = (str(ncert_concept or "").strip().lower() or "all")
        return (
            f"ncert_v3:{int(bool(include_ncert_global))}|class:{class_part}|subject:{subject}|"
            f"chapter_no:{chapter_no}|chapter_name:{chapter_name}|concept:{concept}"
        )

    def _build_ncert_global_filter(
        self,
        *,
        include_ncert: bool,
        selected_class: Optional[int],
        selected_subject: Optional[str],
        selected_chapter_no: Optional[int],
        selected_chapter_name: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        if not include_ncert:
            return None

        ns = getattr(settings, "NCERT_GLOBAL_PINECONE_NAMESPACE", "NcertDataGlobal")
        conditions: List[Dict[str, Any]] = [
            {"source": {"$eq": "ncert"}},
        ]

        if selected_class is not None:
            conditions.append({"class": {"$eq": int(selected_class)}})

        subject = (str(selected_subject or "").strip().lower() or None)
        if subject:
            conditions.append({"subject": {"$eq": subject}})

        if selected_chapter_no is not None:
            conditions.append({"chapter_no": {"$eq": int(selected_chapter_no)}})

        chapter_name = (str(selected_chapter_name or "").strip().lower() or None)
        if chapter_name:
            conditions.append({"chapter_name": {"$eq": chapter_name}})

        if len(conditions) == 1:
            meta_filter = conditions[0]
        else:
            meta_filter = {"$and": conditions}
        
        print(
            f"[TUTOR_FILTER_BUILD] class={selected_class} subject={selected_subject} "
            f"chapter_no={selected_chapter_no} chapter_name={selected_chapter_name} "
            f"-> filter={meta_filter}"
        )
        return meta_filter

    def _merge_scored_matches(
        self,
        *match_groups: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        merged: Dict[str, Dict[str, Any]] = {}
        for group in match_groups:
            for match in group or []:
                if not isinstance(match, dict):
                    continue
                match_id = str(match.get("id") or "").strip()
                if not match_id:
                    continue
                existing = merged.get(match_id)
                if existing is None or float(match.get("score") or 0.0) > float(existing.get("score") or 0.0):
                    merged[match_id] = match
        return sorted(merged.values(), key=lambda x: float(x.get("score") or 0.0), reverse=True)

    async def _retrieve_ncert_global_matches(
        self,
        *,
        query: str,
        ncert_class: Optional[int],
        ncert_subject: Optional[str],
        ncert_chapter_no: Optional[int],
        ncert_chapter_name: Optional[str],
        ncert_concept: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        ns = getattr(settings, "NCERT_GLOBAL_PINECONE_NAMESPACE", "NcertDataGlobal")
        top_k = int(getattr(settings, "NCERT_GLOBAL_RETRIEVAL_TOP_K", 24))
        emb_model = getattr(settings, "NCERT_GLOBAL_EMBEDDING_MODEL", None)
        emb_dims = int(getattr(settings, "NCERT_GLOBAL_EMBEDDING_DIMENSIONS", 1024))

        ncert_vs = PineconeVectorStore(
            METRICS_TENANT_NCERT,
            namespace_override=ns,
            embedding_model_override=emb_model,
            embedding_dimensions_override=emb_dims,
        )
        emb = await ncert_vs.generate_embedding(
            query,
            metrics_user_id=self.user_id,
            metrics_feature_tag="ncert_global_query_embedding",
        )

        meta_filter = self._build_ncert_global_filter(
            include_ncert=True,
            selected_class=ncert_class,
            selected_subject=ncert_subject,
            selected_chapter_no=ncert_chapter_no,
            selected_chapter_name=ncert_chapter_name,
        )

        print(f"\n[TUTOR_QUERY_PINECONE] Querying {ns} with filter={meta_filter}")
        raw = await ncert_vs.query_vectors(emb, top_k=top_k, filter=meta_filter)
        gmatches = list(raw.get("matches") or [])
        print(f"[TUTOR_QUERY_PINECONE_RESULT] Got {len(gmatches)} raw matches from Pinecone")
        
        # DEBUG: Log metadata of each raw match
        if gmatches:
            print(f"\n[DEBUG] Raw Pinecone Results - Metadata of each chunk:")
            for idx, match in enumerate(gmatches, 1):
                md = (match.get("metadata") if isinstance(match, dict) else getattr(match, "metadata", None)) or {}
                match_class = md.get("class") or md.get("class_num")
                match_subject = md.get("subject")
                match_chapter_no = md.get("chapter_no")
                match_chapter_name = md.get("chapter_name")
                match_score = float(match.get("score") or 0) if isinstance(match, dict) else float(getattr(match, "score", 0) or 0)
                print(f"  [{idx}] class={match_class}, subject={match_subject}, chapter_no={match_chapter_no}, chapter_name={match_chapter_name}, score={match_score:.4f}")

        target_subject = (str(ncert_subject or "").strip().lower() or None)
        requested_class = int(ncert_class) if ncert_class is not None else None
        requested_chapter_no = int(ncert_chapter_no) if ncert_chapter_no is not None else None
        requested_chapter_name = (str(ncert_chapter_name or "").strip().lower() or None)
        requested_concept = (str(ncert_concept or "").strip().lower() or None)
        
        print(f"\n[DEBUG] FILTER CRITERIA:")
        print(f"  requested_class={requested_class} (type={type(requested_class)})")
        print(f"  target_subject={target_subject} (type={type(target_subject)})")
        print(f"  requested_chapter_no={requested_chapter_no} (type={type(requested_chapter_no)})")
        print(f"  requested_chapter_name={requested_chapter_name} (type={type(requested_chapter_name)})")
        print(f"  requested_concept={requested_concept}")

        def _coerce_int(value: Any) -> Optional[int]:
            if value is None:
                return None
            if isinstance(value, bool):
                return None
            if isinstance(value, (int, float)):
                return int(value)
            if isinstance(value, str):
                v = value.strip()
                if v.isdigit():
                    return int(v)
            return None

        def _match_passes(m: Any, *, enforce_chapter_name: bool) -> tuple[bool, str, dict]:
            md = (m.get("metadata") if isinstance(m, dict) else getattr(m, "metadata", None)) or {}
            md_class = _coerce_int(md.get("class") or md.get("class_num"))
            md_subject = str(md.get("subject") or "").strip().lower()
            md_chapter_no = _coerce_int(md.get("chapter_no"))
            md_chapter_name = str(md.get("chapter_name") or "").strip().lower()
            md_source = str(md.get("source") or "").strip().lower()

            if md_source and md_source != "ncert":
                return False, f"source mismatch (requested='ncert', got='{md_source}')", md
            if requested_class is not None and md_class != requested_class:
                return False, f"class mismatch (requested={requested_class}, got={md_class})", md
            if target_subject and md_subject != target_subject:
                return False, f"subject mismatch (requested='{target_subject}', got='{md_subject}')", md
            if requested_chapter_no is not None and md_chapter_no != requested_chapter_no:
                return False, f"chapter_no mismatch (requested={requested_chapter_no}, got={md_chapter_no})", md
            if enforce_chapter_name and requested_chapter_name and md_chapter_name != requested_chapter_name:
                return False, (
                    f"chapter_name mismatch (requested='{requested_chapter_name}', got='{md_chapter_name}')"
                ), md
            if requested_concept:
                hint = str(md.get("concept_hint") or "").strip().lower()
                if requested_concept not in hint and hint.find(requested_concept) < 0:
                    if not any(
                        token in hint
                        for token in requested_concept.split("-")
                        if len(token) >= 3
                    ):
                        return False, f"concept mismatch (requested='{requested_concept}', hint='{hint[:80]}')", md
            return True, "", md

        filtered: List[Any] = []
        failed_filters_count = 0
        print(f"\n[DEBUG] POST-PROCESSING FILTER VALIDATION:")
        for idx, m in enumerate(gmatches, 1):
            ok, reason, md = _match_passes(m, enforce_chapter_name=True)
            if not ok:
                print(f"  [{idx}] REJECTED: {reason}")
                failed_filters_count += 1
                continue
            md_class = _coerce_int(md.get("class") or md.get("class_num"))
            md_subject = str(md.get("subject") or "").strip().lower()
            md_chapter_no = _coerce_int(md.get("chapter_no"))
            md_chapter_name = str(md.get("chapter_name") or "").strip().lower()
            print(
                f"  [{idx}] ACCEPTED: class={md_class}, subject={md_subject}, "
                f"chapter_no={md_chapter_no}, chapter_name={md_chapter_name}"
            )
            filtered.append(m)

        if (
            not filtered
            and requested_chapter_no is not None
            and requested_chapter_name
        ):
            print(
                "\n[TUTOR_POSTPROCESS_FILTER] Soft fallback: relaxing chapter_name filter "
                f"(chapter_no={requested_chapter_no} kept)"
            )
            for idx, m in enumerate(gmatches, 1):
                ok, reason, md = _match_passes(m, enforce_chapter_name=False)
                if not ok:
                    continue
                md_class = _coerce_int(md.get("class") or md.get("class_num"))
                md_subject = str(md.get("subject") or "").strip().lower()
                md_chapter_no = _coerce_int(md.get("chapter_no"))
                md_chapter_name = str(md.get("chapter_name") or "").strip().lower()
                print(
                    f"  [{idx}] ACCEPTED (soft): class={md_class}, subject={md_subject}, "
                    f"chapter_no={md_chapter_no}, chapter_name={md_chapter_name}"
                )
                filtered.append(m)

        if len(filtered) != len(gmatches) or failed_filters_count > 0:
            print(
                f"\n[TUTOR_POSTPROCESS_FILTER] Total matches: {len(gmatches)}, Rejected: {failed_filters_count}, Kept: {len(filtered)}"
            )
        gmatches = filtered

        def _norm(m: Any) -> Dict[str, Any]:
            if isinstance(m, dict):
                metadata = dict(m.get("metadata") or {})
                match_id = m.get("id")
                score = float(m.get("score") or 0)
            else:
                metadata = dict(getattr(m, "metadata", None) or {})
                match_id = getattr(m, "id", None)
                score = float(getattr(m, "score", 0) or 0)
            metadata.setdefault("source", "ncert")
            metadata.setdefault("knowledge_namespace", ns)
            metadata.setdefault("source_type", "ncert_global")
            return {
                "id": match_id,
                "score": score,
                "metadata": metadata,
            }

        normalized = []
        for match in gmatches:
            item = _norm(match)
            if item.get("id"):
                normalized.append(item)
        if not normalized:
            print(f"[TUTOR_RETRIEVAL_COMPLETE] No NCERT matches found after filtering")
            return []
        
        print(f"[TUTOR_RETRIEVAL_COMPLETE] Retrieved {len(normalized)} NCERT matches, now applying hybrid scoring")
        result = self.hybrid_retriever.combine_results(normalized, query)
        print(f"[TUTOR_HYBRID_SCORE] Hybrid scoring complete: {len(result)} matches after reranking")
        return result

    async def retrieve_ncert_chapter_matches(
        self,
        *,
        query: str,
        ncert_class: Optional[int],
        ncert_subject: Optional[str],
        ncert_chapter_no: Optional[int],
        ncert_chapter_name: Optional[str],
        ncert_concept: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """NCERT-only retrieval for tutor bootstrap/prepare (skips tenant RAG pipeline)."""
        return await self._retrieve_ncert_global_matches(
            query=query,
            ncert_class=ncert_class,
            ncert_subject=ncert_subject,
            ncert_chapter_no=ncert_chapter_no,
            ncert_chapter_name=ncert_chapter_name,
            ncert_concept=ncert_concept,
        )

    async def _merge_ncert_global_hybrid(
        self,
        *,
        primary_query: str,
        query_embedding: List[float],
        hybrid_matches: List[Dict[str, Any]],
        ncert_class: Optional[int],
        ncert_subject: Optional[str],
        ncert_chapter_no: Optional[int],
        ncert_chapter_name: Optional[str],
        ncert_concept: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Append hybrid-scored hits from Pinecone namespace NcertDataGlobal."""
        print(f"[TUTOR_MERGE_START] Merging {len(hybrid_matches)} primary matches with NCERT global")
        global_hybrid = await self._retrieve_ncert_global_matches(
            query=primary_query,
            ncert_class=ncert_class,
            ncert_subject=ncert_subject,
            ncert_chapter_no=ncert_chapter_no,
            ncert_chapter_name=ncert_chapter_name,
            ncert_concept=ncert_concept,
        )
        if not global_hybrid:
            print(f"[TUTOR_MERGE_COMPLETE] No NCERT matches to merge, returning {len(hybrid_matches)} original matches")
            return hybrid_matches
        merged = self._merge_scored_matches(hybrid_matches, global_hybrid)
        print(f"[TUTOR_MERGE_COMPLETE] Merged {len(hybrid_matches)} primary + {len(global_hybrid)} NCERT = {len(merged)} total matches")
        return merged

    async def _maybe_blend_derived(
        self,
        matches: List[Dict[str, Any]],
        query: Optional[str],
        *,
        concept_node_id: Optional[str] = None,
    ) -> tuple[List[Dict[str, Any]], bool]:
        """Blend curated derived artifacts into KB matches when IIL is enabled."""
        if not getattr(settings, "IIL_ENABLED", False) or not (query or "").strip():
            return matches, False
        derived = await retrieve_derived_knowledge(
            self.tenant_id,
            query,
            concept_node_id=concept_node_id,
            top_k=max(2, round(len(matches) * settings.IIL_BLENDING_DERIVED_WEIGHT)) if matches else 4,
        )
        if not derived:
            return matches, False
        return blend_retrieval_results(matches, derived), True
    
    async def retrieve(
        self,
        query_embedding: Optional[List[float]] = None,
        query: Optional[str] = None,
        top_k: int = None,
        filter: Optional[Dict] = None,
        conversation_history: Optional[List[Dict]] = None,
        classified_intent: Optional[str] = None,
        classified_intent_confidence: Optional[float] = None,
        scope: Optional[str] = None,
        requires_retrieval: Optional[bool] = None,
        requires_attachment: Optional[bool] = None,
        include_ncert_global: bool = False,
        ncert_class: Optional[int] = None,
        ncert_subject: Optional[str] = None,
        ncert_chapter_no: Optional[int] = None,
        ncert_chapter_name: Optional[str] = None,
        ncert_concept: Optional[str] = None,
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
            classified_intent: Optional pre-classified intent slug (e.g. from LangGraph)
            classified_intent_confidence: Confidence for pre-classified intent (enables routing gate)
            scope: Optional retrieval-scope hint from IntentClassifier
                (whole_document | section | fact | unspecified); passed to ScopeNarrower.
            requires_retrieval: Optional advisory flag from IntentClassifier.
            requires_attachment: Optional advisory flag from IntentClassifier.

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
            cache_scope = self._build_retrieval_cache_scope(
                include_ncert_global=include_ncert_global,
                ncert_class=ncert_class,
                ncert_subject=ncert_subject,
                ncert_chapter_no=ncert_chapter_no,
                ncert_chapter_name=ncert_chapter_name,
                ncert_concept=ncert_concept,
            )
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
            # DEBUG: Log NCERT global merging decision in simple path
            print(f"[RETRIEVAL_SIMPLE_NCERT] include_ncert_global={include_ncert_global}")
            print(f"[RETRIEVAL_SIMPLE_NCERT] ENABLE_NCERT_GLOBAL_IN_CHAT={getattr(settings, 'ENABLE_NCERT_GLOBAL_IN_CHAT', False)}")
            print(f"[RETRIEVAL_SIMPLE_NCERT] Will merge NCERT global: {query and include_ncert_global and getattr(settings, 'ENABLE_NCERT_GLOBAL_IN_CHAT', False)}")
            
            if (
                query
                and include_ncert_global
                and getattr(settings, "ENABLE_NCERT_GLOBAL_IN_CHAT", False)
            ):
                try:
                    print("[RETRIEVAL_SIMPLE_NCERT] OK Merging NCERT global matches")
                    ncert_matches = await self._retrieve_ncert_global_matches(
                        query=query,
                        ncert_class=ncert_class,
                        ncert_subject=ncert_subject,
                        ncert_chapter_no=ncert_chapter_no,
                        ncert_chapter_name=ncert_chapter_name,
                        ncert_concept=ncert_concept,
                    )
                    if ncert_matches:
                        matches = self._merge_scored_matches(matches, ncert_matches)
                        debug_trace["guardrails_applied"].append("ncert_global_merged")
                except Exception as e:
                    print(f"[RAG_PIPELINE] NCERT global merge skipped: {e}")
            else:
                print("[RETRIEVAL_SIMPLE_NCERT] SKIP NOT merging NCERT global (checkbox not checked or setting disabled)")
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
            blended, derived_hit = await self._maybe_blend_derived(matches, query)
            if derived_hit:
                matches = blended
                results["matches"] = matches
                results["derived_hit"] = True
                debug_trace["guardrails_applied"].append("derived_knowledge_blended")
            if settings.RAG_DEBUG:
                results["debug_trace"] = debug_trace
            # Metadata for downstream (e.g. chat generator prompt) — simple path has no scope/rewrite
            results["focused_query"] = query
            results["rewritten_queries"] = [query]
            results["retrieval_cache_scope"] = cache_scope
            return results
        
        # Phase 2: Enhanced retrieval pipeline
        if query is None:
            raise ValueError("query required when USE_RETRIEVAL_AGENTS is True")
        
        self._log("START", f"Retrieval pipeline started", {"query": query, "top_k": top_k})
        
        # 0. Query Complexity Scoring (skip expensive ops for simple queries)
        complexity_result = self.complexity_scorer.score_complexity(query)
        should_skip_rerank = complexity_result.get("should_skip_rerank", False)
        should_skip_confidence = complexity_result.get("should_skip_confidence", False)
        should_skip_rewrite = complexity_result.get("should_skip_rewrite", False)
        
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
            if classified_intent_confidence is not None:
                try:
                    intent_confidence = float(classified_intent_confidence)
                except (TypeError, ValueError):
                    intent_confidence = 0.8
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

        scope_focused_query = query
        scope_key_terms: list = []
        if self.scope_narrower and not should_skip_rerank:
            try:
                scope_result = await self.scope_narrower.narrow_scope(
                    query=query,
                    conversation_history=conversation_history,
                    scope=scope,
                )
                scope_focused_query = str(scope_result.get("focused_query") or query).strip() or query
                scope_key_terms = list(scope_result.get("key_terms") or [])
                scope_max = int(scope_result.get("max_chunks") or top_k)
                top_k = min(top_k, max(3, scope_max))
                debug_trace["scope_narrower"] = {
                    "focused_query": scope_focused_query,
                    "max_chunks": top_k,
                    "key_terms": scope_key_terms[:7],
                }
                self._log("SCOPE", "Scope narrowed", debug_trace["scope_narrower"])
            except Exception as exc:
                print(f"[RAG_PIPELINE] Scope narrower failed: {exc}")

        retrieval_strategy = resolve_retrieval_strategy(
            intent=intent or UserIntent.QUESTION,
            intent_confidence=intent_confidence,
            query=query,
            complexity_result=complexity_result,
            min_confidence=float(getattr(settings, "RETRIEVAL_INTENT_ROUTING_MIN_CONFIDENCE", 0.55)),
            explanation_min_words_for_decomposition=int(
                getattr(settings, "QUERY_DECOMPOSITION_MIN_QUERY_WORDS_EXPLANATION", 12)
            ),
        )
        debug_trace["retrieval_strategy"] = {
            "initial_retrieval_k_multiplier": retrieval_strategy.initial_retrieval_k_multiplier,
            "enable_query_decomposition": retrieval_strategy.enable_query_decomposition_for_this_request,
            "skip_mmr": retrieval_strategy.skip_mmr,
            "mmr_target_multiplier": retrieval_strategy.mmr_target_multiplier,
        }
        
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
        rewrite_input = scope_focused_query
        focused_query = rewrite_input
        key_terms: list = list(scope_key_terms)
        rewritten_queries = [rewrite_input]
        rewrite_confidence = 1.0
        used_rewrites = False
        cache_scope = self._build_retrieval_cache_scope(
            include_ncert_global=include_ncert_global,
            ncert_class=ncert_class,
            ncert_subject=ncert_subject,
            ncert_chapter_no=ncert_chapter_no,
            ncert_chapter_name=ncert_chapter_name,
            ncert_concept=ncert_concept,
        )

        source_ids_list = list(filter.get("source_id", {}).get("$in", [])) if filter else None
        cached_rewrite = None
        if not should_skip_rewrite:
            cached_rewrite = self.retrieval_cache.get_rewrite(
                rewrite_input,
                source_ids_list,
                cache_extra=cache_scope,
            )

        if should_skip_rewrite:
            rewritten_queries = [rewrite_input]
            rewrite_confidence = 1.0
            used_rewrites = False
            debug_trace["rewrite_skipped"] = True
            debug_trace["guardrails_applied"].append("simple_query_skip_rewrite")
        elif cached_rewrite:
            rewritten_queries = cached_rewrite
            rewrite_confidence = 1.0
            used_rewrites = True
            self._log("CACHE", f"Using cached query rewrite", {"rewritten_queries": rewritten_queries})
            debug_trace["rewrite_cache_hit"] = True
        else:
            rewrite_result = await trace_async(
                "Retrieval/query_rewrite",
                self.query_rewriter.rewrite_query(
                    query=rewrite_input,
                    conversation_history=conversation_history,
                    max_rewrites=2,
                    confidence_threshold=settings.QUERY_REWRITE_CONFIDENCE_THRESHOLD,
                    scope=scope,
                    requires_retrieval=requires_retrieval,
                    requires_attachment=requires_attachment,
                ),
                input_summary={"raw_query": trace_snippet(rewrite_input, 240)},
                output_fn=lambda r: {
                    "rewritten_queries": [trace_snippet(x, 160) for x in (r or {}).get("queries", [])[:4]],
                    "confidence": (r or {}).get("confidence"),
                },
                feature_tag="query_rewriter",
            )
            rewritten_queries = rewrite_result.get("queries", [rewrite_input])
            rewrite_confidence = rewrite_result.get("confidence", 0.0)
            used_rewrites = rewrite_result.get("used_rewrites", False)

            if used_rewrites and rewritten_queries:
                self.retrieval_cache.set_rewrite(
                    rewrite_input,
                    rewritten_queries,
                    source_ids_list,
                    cache_extra=cache_scope,
                )
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

        if is_factual_recall_query(query) or is_factual_recall_query(focused_query):
            seen_lower = {str(x).strip().lower() for x in rewritten_queries if x}
            for v in extra_factual_retrieval_variants(focused_query):
                vl = v.strip().lower()
                if vl and vl not in seen_lower:
                    rewritten_queries.append(v)
                    seen_lower.add(vl)
            debug_trace["guardrails_applied"].append("factual_recall_variants")
        
        primary_query = rewritten_queries[0] if rewritten_queries else query

        # 3. Optional: Query Decomposition (intent-gated; shadow mode logs only)
        decompose_on = getattr(settings, "ENABLE_QUERY_DECOMPOSITION", False)
        decompose_shadow = getattr(settings, "ENABLE_QUERY_DECOMPOSITION_SHADOW", False)
        run_decomposer = (
            self.query_decomposer is not None
            and (decompose_on or decompose_shadow)
            and retrieval_strategy.enable_query_decomposition_for_this_request
            and not should_skip_rerank
        )
        if run_decomposer:
            dec = await trace_async(
                "Retrieval/query_decompose",
                self.query_decomposer.decompose(
                    query=primary_query,
                    max_sub_queries=getattr(settings, "QUERY_DECOMPOSITION_MAX_SUB_QUERIES", 4),
                    scope=scope,
                    requires_retrieval=requires_retrieval,
                    requires_attachment=requires_attachment,
                ),
                input_summary={"query": trace_snippet(primary_query, 240)},
                output_fn=lambda r: {
                    "primary_concept": trace_snippet((r or {}).get("primary_concept", ""), 120),
                    "sub_queries": [trace_snippet(x, 120) for x in ((r or {}).get("sub_queries") or [])[:6]],
                },
                feature_tag="query_decomposer",
            )
            sub_queries = (dec or {}).get("sub_queries") or []
            debug_trace["decomposition_used"] = bool(sub_queries)
            debug_trace["decomposition_sub_query_count"] = len(sub_queries)
            debug_trace["query_decomposition"] = {
                "primary_concept": (dec or {}).get("primary_concept", ""),
                "sub_queries": sub_queries,
                "shadow_only": bool(decompose_shadow and not decompose_on),
            }
            if decompose_shadow and not decompose_on:
                debug_trace["guardrails_applied"].append("query_decomposition_shadow")
            elif decompose_on and sub_queries:
                seen = {str(x).strip().lower() for x in rewritten_queries if x}
                for sq in sub_queries:
                    s = str(sq or "").strip()
                    if not s:
                        continue
                    sl = s.lower()
                    if sl in seen:
                        continue
                    rewritten_queries.append(s)
                    seen.add(sl)
                debug_trace["guardrails_applied"].append("query_decomposition")
        
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
        initial_retrieval_k = max(
            int(top_k * retrieval_strategy.initial_retrieval_k_multiplier),
            20,
        )
        
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
        
        # DEBUG: Log source_id of initial vector matches
        print(f"[VECTOR_PHASE] Retrieved {len(vector_matches)} chunks with filter={filter}")
        vector_source_ids = set()
        for chunk in vector_matches[:5]:  # Show first 5
            src = chunk.get("metadata", {}).get("source_id", "UNKNOWN")
            vector_source_ids.add(src)
            print(f"  [VECTOR] chunk_id={chunk.get('id')[:20] if chunk.get('id') else 'UNKNOWN'} | source_id={src}")
        if len(vector_matches) > 5:
            print(f"  ... and {len(vector_matches) - 5} more chunks")
        print(f"[VECTOR_PHASE] Unique sources in initial vector retrieval: {vector_source_ids}")
        
        debug_trace["retrieved_chunks_initial"] = {
            "count": len(vector_matches),
            "ids": [m.get("id") for m in vector_matches[:10]]  # First 10 IDs
        }
        
        print(f"[RAG_PIPELINE] Stage: RETRIEVE | Chunks: {len(vector_matches)}")
        self._log("RETRIEVAL", f"Initial vector retrieval", {
            "count": len(vector_matches),
            "top_k_requested": initial_retrieval_k
        })
        
        # Contextual BM25 + rank fusion (optional; closest to guide).
        if getattr(settings, "ENABLE_BM25_RANK_FUSION", False) and self.li_retriever is None:
            try:
                # Build BM25 corpus from all chunks in active sources (via Pinecone filter query).
                # For large corpora, use a cap to avoid runaway costs.
                source_ids = []
                if filter and isinstance(filter, dict):
                    if isinstance(filter.get("source_id"), dict) and "$in" in filter.get("source_id", {}):
                        source_ids = list(filter.get("source_id", {}).get("$in", []) or [])
                bm25_corpus_cap = int(getattr(settings, "BM25_CORPUS_MAX_CHUNKS", 5000))
                bm25_top_k = max(200, min(bm25_corpus_cap, 10000))
                bm25_docs = []
                if source_ids:
                    dummy = [0.0] * int(getattr(settings, "OPENAI_EMBEDDING_DIMENSIONS", 1024))
                    raw = await self.vector_store.query_vectors(
                        query_embedding=dummy,
                        top_k=bm25_top_k,
                        filter={"source_id": {"$in": source_ids}},
                    )
                    all_matches = raw.get("matches", []) or []
                else:
                    all_matches = vector_matches

                for m in all_matches[:bm25_corpus_cap]:
                    md = (m.get("metadata", {}) if isinstance(m, dict) else getattr(m, "metadata", {})) or {}
                    raw_text = str(md.get("text", "") or "")
                    if not raw_text:
                        continue
                    bm25_docs.append(
                        (
                            str((m.get("id") if isinstance(m, dict) else getattr(m, "id", "")) or ""),
                            raw_text,
                            {"metadata": md},
                        )
                    )

                bm25 = LocalBM25(bm25_docs) if bm25_docs else None
                sparse_matches = bm25.query(primary_query, top_n=int(getattr(settings, "BM25_FUSION_TOP_K", 150))) if bm25 else []

                fused = rrf_fuse(
                    dense=[dict(x) for x in vector_matches if isinstance(x, dict)],
                    sparse=sparse_matches,
                    top_n=int(getattr(settings, "BM25_FUSION_TOP_K", 150)),
                )

                # Now apply hybrid keyword normalization on fused list (small candidate pool).
                hybrid_matches = self.hybrid_retriever.combine_results(
                    vector_results=fused,
                    query=primary_query,
                )
            except Exception:
                hybrid_matches = self.hybrid_retriever.combine_results(
                    vector_results=vector_matches,
                    query=primary_query,
                )
        else:
            # Combine with keyword search using hybrid retriever (normalized scores)
            hybrid_matches = self.hybrid_retriever.combine_results(
                vector_results=vector_matches,
                query=primary_query,
            )
        
        # DEBUG: Log source_id of hybrid matches (before NCERT merge)
        print(f"[HYBRID_PHASE] After hybrid combining: {len(hybrid_matches)} chunks")
        hybrid_source_ids = set()
        for chunk in hybrid_matches[:5]:  # Show first 5
            src = chunk.get("metadata", {}).get("source_id", "UNKNOWN")
            hybrid_source_ids.add(src)
            print(f"  [HYBRID] chunk_id={chunk.get('id')[:20] if chunk.get('id') else 'UNKNOWN'} | source_id={src}")
        if len(hybrid_matches) > 5:
            print(f"  ... and {len(hybrid_matches) - 5} more chunks")
        print(f"[HYBRID_PHASE] Unique sources after hybrid (before NCERT): {hybrid_source_ids}")

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

        # DEBUG: Log NCERT global merging decision in Phase 2
        print(f"[RETRIEVAL_PHASE2_NCERT] include_ncert_global={include_ncert_global}")
        print(f"[RETRIEVAL_PHASE2_NCERT] ENABLE_NCERT_GLOBAL_IN_CHAT={getattr(settings, 'ENABLE_NCERT_GLOBAL_IN_CHAT', False)}")
        print(f"[RETRIEVAL_PHASE2_NCERT] USE_RETRIEVAL_AGENTS={settings.USE_RETRIEVAL_AGENTS}")
        print(f"[RETRIEVAL_PHASE2_NCERT] hybrid_retriever is not None={self.hybrid_retriever is not None}")
        print(f"[RETRIEVAL_PHASE2_NCERT] Will merge NCERT global: {include_ncert_global and getattr(settings, 'ENABLE_NCERT_GLOBAL_IN_CHAT', False) and settings.USE_RETRIEVAL_AGENTS and self.hybrid_retriever is not None}")
        
        if (
            include_ncert_global
            and getattr(settings, "ENABLE_NCERT_GLOBAL_IN_CHAT", False)
            and settings.USE_RETRIEVAL_AGENTS
            and self.hybrid_retriever is not None
        ):
            try:
                print("[RETRIEVAL_PHASE2_NCERT] OK Merging NCERT global matches")
                hybrid_matches = await self._merge_ncert_global_hybrid(
                    primary_query=primary_query,
                    query_embedding=query_embedding,
                    hybrid_matches=hybrid_matches,
                    ncert_class=ncert_class,
                    ncert_subject=ncert_subject,
                    ncert_chapter_no=ncert_chapter_no,
                    ncert_chapter_name=ncert_chapter_name,
                    ncert_concept=ncert_concept,
                )
                debug_trace["guardrails_applied"].append("ncert_global_merged")
                debug_trace["after_hybrid_merge"] = {"count": len(hybrid_matches)}
            except Exception as e:
                print(f"[RAG_PIPELINE] NCERT global merge skipped: {e}")
        else:
            print("[RETRIEVAL_PHASE2_NCERT] SKIP NOT merging NCERT global (checkbox not checked or setting disabled)")
        
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
                    if (
                        include_ncert_global
                        and getattr(settings, "ENABLE_NCERT_GLOBAL_IN_CHAT", False)
                    ):
                        ncert_variant_matches = await self._retrieve_ncert_global_matches(
                            query=rewritten_query,
                            ncert_class=ncert_class,
                            ncert_subject=ncert_subject,
                            ncert_chapter_no=ncert_chapter_no,
                            ncert_chapter_name=ncert_chapter_name,
                            ncert_concept=ncert_concept,
                        )
                        variant_hybrid = self._merge_scored_matches(
                            variant_hybrid,
                            ncert_variant_matches,
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
        skip_mmr = skip_mmr or retrieval_strategy.skip_mmr
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
            mmr_pool = max(
                1,
                int(top_k * float(retrieval_strategy.mmr_target_multiplier)),
            )
            diverse_matches = self.mmr_diversity.select_diverse_chunks(
                chunks=hybrid_matches,
                query_embedding=query_embedding,
                top_k=min(mmr_pool, len(hybrid_matches))  # Get more for reranking
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
            cached_rerank = self.retrieval_cache.get_rerank(
                primary_query,
                source_ids_list,
                cache_extra=cache_scope,
            )
            
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
                    self.retrieval_cache.set_rerank(
                        primary_query,
                        reranked_matches,
                        source_ids_list,
                        cache_extra=cache_scope,
                    )
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

        _cw_t0 = time.perf_counter()
        ca_enabled = bool(getattr(settings, "ENABLE_CONTEXT_AWARE_RETRIEVAL_WEIGHTING", False))
        if ca_enabled:
            try:
                reranked_matches = apply_context_aware_scores(
                    list(reranked_matches),
                    primary_query,
                    max_boost=float(getattr(settings, "CONTEXT_AWARE_WEIGHTING_MAX_BOOST", 0.15)),
                    intent=intent,
                )
                debug_trace["guardrails_applied"].append("context_aware_weighting_post_rerank")
            except Exception:
                pass
        record_retrieval_span(
            "Retrieval/context_aware_weighting",
            (time.perf_counter() - _cw_t0) * 1000,
            input_summary={
                "enabled": ca_enabled,
                "chunks_in": len(reranked_matches),
            },
            output_summary={"chunks_out": len(reranked_matches)},
            feature_tag="context_aware_weighting",
        )
        
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
        
        # DEBUG: Log source_id and content preview of each chunk
        print(f"[RAG_PIPELINE] FINAL: {len(selected_matches)} chunks ready for LLM (token_size: {final_token_size})")
        print(f"[CHUNK_SOURCES] Retrieving chunks with filter={filter}:")
        for i, chunk in enumerate(selected_matches, 1):
            chunk_meta = chunk.get("metadata", {})
            source_id = chunk_meta.get("source_id", "UNKNOWN")
            chunk_id = chunk.get("id", "UNKNOWN")
            text_preview = (chunk_meta.get("text", "")[:100] + "...") if chunk_meta.get("text") else "NO TEXT"
            print(f"  [{i}] source_id={source_id} | chunk_id={chunk_id} | text={text_preview}")
        
        blended, derived_hit = await self._maybe_blend_derived(
            selected_matches,
            query or focused_query,
            concept_node_id=ncert_concept,
        )
        if derived_hit:
            selected_matches = blended
            debug_trace["guardrails_applied"].append("derived_knowledge_blended")

        # Return results in expected format
        result = {
            "matches": selected_matches,
            "intent": intent,
            "intent_confidence": intent_confidence,
            "key_terms": key_terms,
            "focused_query": focused_query,
            "rewritten_queries": rewritten_queries,
            "derived_hit": derived_hit,
            "metadata": {
                "total_retrieved": len(hybrid_matches),
                "after_mmr": len(diverse_matches),
                "after_reranking": len(reranked_matches),
                "final_selected": len(selected_matches),
                "derived_hit": derived_hit,
            }
        }
        
        # Add debug trace if enabled
        if settings.RAG_DEBUG:
            result["debug_trace"] = debug_trace
        
        return result


async def retrieve_derived_knowledge(
    tenant_id: str,
    query: str,
    *,
    concept_node_id: Optional[str] = None,
    top_k: int = 4,
) -> List[Dict[str, Any]]:
    """Retrieve curated derived artifacts from tenant derived Pinecone namespace."""
    if not settings.PINECONE_API_KEY or not query.strip():
        return []
    try:
        from packages.core.iil.derived_embedder import derived_namespace_for_tenant

        embedder = Embedder(tenant_id)
        vector = await embedder.generate_embedding(query[:2000])
        if not vector:
            return []
        store = PineconeVectorStore(
            tenant_id,
            namespace_override=derived_namespace_for_tenant(tenant_id),
        )
        filt: Dict[str, Any] = {"source_type": "derived"}
        if concept_node_id:
            filt["concept_node_id"] = concept_node_id
        results = await store.query_vectors(vector=vector, top_k=top_k, filter=filt)
        matches = []
        for m in results.get("matches", []):
            meta = m.get("metadata") or {}
            matches.append({
                "id": m.get("id"),
                "score": m.get("score", 0),
                "metadata": {**meta, "source_type": "derived"},
                "text": meta.get("text") or meta.get("content") or "",
            })
        return matches
    except Exception as exc:
        print(f"[IIL] derived retrieval failed: {exc}")
        return []


def blend_retrieval_results(
    kb_matches: List[Dict[str, Any]],
    derived_matches: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Weighted merge: default 70% KB slots, 30% derived (spec §4.7)."""
    if not derived_matches:
        return kb_matches
    if not kb_matches:
        return derived_matches
    kb_w = settings.IIL_BLENDING_KB_WEIGHT
    derived_w = settings.IIL_BLENDING_DERIVED_WEIGHT
    total = max(kb_w + derived_w, 0.01)
    kb_slots = min(len(kb_matches), max(1, round(len(kb_matches) * kb_w / total)))
    derived_slots = min(len(derived_matches), max(1, round(len(derived_matches) * derived_w / total)))
    merged = list(kb_matches[:kb_slots]) + list(derived_matches[:derived_slots])
    return merged
