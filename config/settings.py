"""
Application Configuration

Loads environment variables and provides settings for the application.
Uses Pydantic Settings for validation and type safety.

🔒 SINGLE SOURCE OF TRUTH for all config
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Any, Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""    

    # App
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"
    
    # Database
    DATABASE_URL: str = Field(..., description="PostgreSQL database connection string (required)")
    # Echo logs every SQL statement — very noisy and slower; enable only when debugging queries
    SQLALCHEMY_ECHO: bool = False
    DB_POOL_SIZE: int = 15
    DB_MAX_OVERFLOW: int = 25
    # Supabase session pooler (often port 5432) is connection-limited; this repo caps pool_size/max_overflow
    # to avoid MaxClientsInSessionMode. In development you may disable the cap if you control concurrency.
    DB_SUPABASE_5432_POOL_CAP_ENABLED: bool = False
    # Production gate: if True, DB pool timeouts return safe empty fallbacks for list endpoints
    # instead of raising 500s. Prefer fixing root causes (pool sizing / transaction pooler) but this
    # prevents noisy UI failures during incidents.
    DB_FAIL_OPEN_ON_POOL_TIMEOUT: bool = True
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    
    # Vector Database
    PINECONE_API_KEY: str = ""
    PINECONE_ENVIRONMENT: str = "us-east-1"
    PINECONE_INDEX_NAME: str = "scholarsync-vectors"
    
    # LLM APIs
    OPENAI_API_KEY: str = ""
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_EMBEDDING_DIMENSIONS: int = 1024
    GEMINI_API_KEY: str = ""

    # Plan B: LangGraph chat orchestration
    USE_LANGGRAPH_CHAT: bool = True
    # Route greetings / thanks / small talk away from Pinecone (fast path, no vector search)
    ENABLE_DIALOG_ROUTER: bool = True

    # OpenAI Moderation
    OPENAI_MODERATION_MODEL: str = "omni-moderation-latest"
    # If any category score >= this, treat as blocked (in addition to API `flagged`)
    MODERATION_CATEGORY_SCORE_THRESHOLD: float = 0.35
    # Production gate: disable score-threshold blocking by default to avoid false positives on benign educational content.
    # When False, only `flagged` or explicit True categories will block.
    MODERATION_BLOCK_ON_CATEGORY_SCORES: bool = False
    # When OpenAI key is set: if False (default), moderation API/network errors refuse (fail closed).
    MODERATION_FAIL_OPEN_ON_ERROR: bool = False
    # Output path: omni-moderation often false-flags educational biology (pain, injury, reflex arcs) as
    # violence/self-harm. When True (default), allow answers that look like scholarly RAG output if only
    # soft categories fire and scores stay below MODERATION_OUTPUT_SENSITIVE_ALLOW_UNDER_SCORE.
    MODERATION_OUTPUT_LENIENT: bool = True
    # Max score for soft categories (violence non-graphic, self-harm non-instructions) to permit bypass with heuristic.
    MODERATION_OUTPUT_SENSITIVE_ALLOW_UNDER_SCORE: float = 0.78
    # Always block output if these substrings appear in a True category name (OpenAI slash or underscore forms).
    # Comma-separated; empty uses built-in defaults in code.
    MODERATION_OUTPUT_HARD_CATEGORY_SUBSTRINGS: str = ""
    # If self-harm/instructions or violence/graphic exceeds this, never bypass.
    MODERATION_OUTPUT_INSTRUCTIONS_BLOCK_MIN: float = 0.22
    MODERATION_OUTPUT_GRAPHIC_VIOLENCE_BLOCK_MIN: float = 0.22

    # Cohere reranking (set via environment in production)
    COHERE_API_KEY: str = ""
    COHERE_RERANK_MODEL: str = "rerank-v3.5"
    
    # Image Generation
    # Uses DALL-E 3 for image generation
    
    # Storage
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = ""
    
    # Authentication
    CLERK_SECRET_KEY: str = ""
    CLERK_ISSUER: str = ""
    CLERK_JWT_PUBLIC_KEY: str = ""  # JWT verification key
    CLERK_JWT_AUDIENCE: str = ""    # <-- added to avoid extra_forbidden error

    # Chunking Configuration
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200  # Deprecated: use CHUNK_OVERLAP_PERCENT instead
    CHUNK_OVERLAP_PERCENT: float = 0.12  # 12% overlap (10-15% range)
    USE_SEMANTIC_CHUNKING: bool = True  # Enable semantic chunking
    
    # RAG Configuration
    TOP_K_CHUNKS: int = 12  # Initial retrieval pool (was 10)
    # Studio: multi-query vector retrieval (no reranker)
    STUDIO_RETRIEVAL_QUERIES_CAP: int = 3  # Max rewritten queries to embed per topic-focused request
    STUDIO_RETRIEVAL_TOP_K_PER_QUERY: int = 10  # Pinecone top_k each vector query
    STUDIO_CONTEXT_MAX_CHUNKS: int = 28  # After merge-by-id, max chunks in context
    # Infographic: richer multi-query retrieval (single-source task); each line = one embed + Pinecone query
    STUDIO_INFOGRAPHIC_RETRIEVAL_QUERIES_CAP: int = 14  # Max broad queries to run (full list has 14 lines)
    STUDIO_INFOGRAPHIC_CONTEXT_MAX_CHUNKS: int = 36  # Wider context merge cap for visual grounding
    STUDIO_RETRIEVAL_NOTE_MAX_CHARS: int = 900  # Prompt line summarizing queries used for search
    # Studio chat_hybrid: ~40% of chunk budget for sources vs conversation (see studio_service)
    STUDIO_HYBRID_SOURCE_CHUNK_FRACTION: float = 0.4
    STUDIO_HYBRID_CHAT_MAX_CHARS: int = 48_000  # Cap formatted transcript size in hybrid prompt
    SIMILARITY_THRESHOLD: float = 0.54  # Context floor; factual/rare terms often score lower than paraphrase-heavy chunks
    CHAT_MAX_TOKENS: int = 2048  # Maximum tokens for chat responses
    # Prior turns included in chat/rag_prompt.j2 (conversation continuity)
    CHAT_PROMPT_MAX_HISTORY_MESSAGES: int = 16
    CHAT_PROMPT_MAX_CHARS_PER_MESSAGE: int = 900
    
    # Phase 2: Retrieval Quality & Cost Guardrails
    USE_RETRIEVAL_AGENTS: bool = True  # Enable Phase 2 agents
    MMR_LAMBDA: float = 0.72  # MMR balance — slight bias to relevance for answer quality
    HYBRID_VECTOR_WEIGHT: float = 0.65  # Hybrid retrieval vector weight
    HYBRID_KEYWORD_WEIGHT: float = 0.35  # Slightly higher keyword weight for names, terms, headings
    MAX_CONTEXT_CHUNKS: int = 12  # Pack more evidence per answer
    MIN_CONTEXT_CHUNKS: int = 7  # Minimum chunks before token budget stops selection
    RAG_DEBUG: bool = False  # Enable detailed debug logging for RAG pipeline
    QUERY_REWRITE_CONFIDENCE_THRESHOLD: float = 0.7  # Logged / reserved; rewrites apply on successful parse
    # Shared transcript limits for query rewriter, scope narrow, intent LLM path
    AGENT_CONVERSATION_MAX_MESSAGES: int = 12
    AGENT_CONVERSATION_MAX_CHARS_PER_MESSAGE: int = 1200
    CONTEXT_TOKEN_BUDGET: int = 4500  # Target token budget for context (~18k chars of chunk text)
    # Whole-document summary: retrieve and pack many chunks (user asked for full-PDF style summaries)
    DOCUMENT_SUMMARY_RETRIEVAL_TOP_K: int = 72  # Pinecone hybrid pool size for summary/overview queries
    DOCUMENT_SUMMARY_MAX_CONTEXT_CHUNKS: int = 64  # Chunks allowed into the LLM context for summaries
    DOCUMENT_SUMMARY_CONTEXT_TOKEN_BUDGET: int = 12000  # Wider token budget for summary context packing
    DOCUMENT_SUMMARY_MIN_CHUNKS: int = 24  # Floor so summaries are not limited to a handful of chunks
    DOCUMENT_SUMMARY_CHAT_MAX_TOKENS: int = 4096  # Longer model output for comprehensive summaries
    DOCUMENT_SUMMARY_MAX_CHUNK_CHARS: int = 550  # Slightly longer excerpts per chunk when summarizing whole docs
    # Map-reduce: fetch all chunks → summarize batches → final summary (whole-file intent)
    USE_WHOLE_FILE_MAP_REDUCE: bool = True
    WHOLE_FILE_MAP_BATCH_SIZE: int = 6  # Chunks per map LLM call (one sentence each)
    WHOLE_FILE_MAX_CHUNKS: int = 500  # Safety cap on chunks per request
    MAX_CHUNK_LENGTH: int = 600  # Per-chunk cap when packing context into the prompt
    # Dedup: only drop chunks if very similar (higher = keep more distinct passages)
    CONTEXT_DEDUP_SIMILARITY_THRESHOLD: float = 0.82
    METADATA_QUERY_MAX_CHUNK_CHARS: int = 900  # Author / copyright / title-page questions need longer excerpts
    USE_CHUNK_COMPRESSION: bool = True  # Compress lower-scoring chunks to reduce tokens

    # ---------------------------
    # Contextual Retrieval (ingestion-time chunk enrichment)
    # ---------------------------
    # Feature flag: enrich chunks with chunk_context/summary/type/section/concept_hint and embed concatenation.
    ENABLE_CONTEXTUAL_RETRIEVAL_INGESTION: bool = True
    # Generate document-level summary once per ingestion to reduce repeated whole-doc tokens.
    ENABLE_CONTEXTUAL_RETRIEVAL_DOC_SUMMARY: bool = True
    # Safety/cost controls (chars, not tokens; token estimation is approximate in code).
    CONTEXTUAL_RETRIEVAL_MAX_DOC_CONTEXT_CHARS: int = 24000
    CONTEXTUAL_RETRIEVAL_MAX_CHUNK_CHARS_FOR_PROMPT: int = 3500
    # Output size targets for contextual metadata.
    CONTEXTUAL_RETRIEVAL_TARGET_CONTEXT_TOKENS: int = 50
    CONTEXTUAL_RETRIEVAL_TARGET_SUMMARY_TOKENS: int = 50
    CONTEXTUAL_RETRIEVAL_TARGET_CONCEPT_HINT_TERMS: int = 8
    # Ingestion throughput guardrails.
    CONTEXTUAL_RETRIEVAL_MAX_CONCURRENCY_PER_DOCUMENT: int = 6
    CONTEXTUAL_RETRIEVAL_MAX_RETRIES: int = 2
    # NCERT global ingest: same long document was repeated per chunk (was ~24k chars × N chunks → huge
    # prompt tokens, slow requests, client timeouts). Cap document excerpt per contextualization call.
    CONTEXTUAL_RETRIEVAL_NCERT_DOC_CONTEXT_CHARS: int = 5000
    CONTEXTUAL_RETRIEVAL_NCERT_MAX_CONCURRENCY: int = 3
    # Optional: generate a one-time compact document sketch and reuse it for each chunk contextualization call.
    # This reduces repeated document tokens and stabilizes section/topic extraction.
    CONTEXTUAL_RETRIEVAL_NCERT_USE_DOC_SKETCH: bool = True
    CONTEXTUAL_RETRIEVAL_NCERT_DOC_SKETCH_CACHE_TTL_SECONDS: int = 3600  # 1 hour
    CONTEXTUAL_RETRIEVAL_NCERT_DOC_SKETCH_MAX_INPUT_CHARS: int = 12000
    CONTEXTUAL_RETRIEVAL_NCERT_DOC_SKETCH_MAX_OUTPUT_TOKENS: int = 700
    CONTEXTUAL_RETRIEVAL_NCERT_DOC_SKETCH_MAX_CHARS: int = 3500
    CONTEXTUAL_RETRIEVAL_NCERT_DOC_SKETCH_MODEL: str = ""  # default: reuse NCERT_GLOBAL_CONTEXT_MODEL
    # Sketch cache backend: disk (default) or redis.
    CONTEXTUAL_RETRIEVAL_NCERT_DOC_SKETCH_CACHE_BACKEND: str = "redis"
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_TIMEOUT_S: float = 1.5
    REDIS_KEY_PREFIX: str = "ncert:doc_sketch:"
    # Normal (tenant) uploads: one-time document sketch for contextual retrieval (reduces repeated doc tokens).
    CONTEXTUAL_RETRIEVAL_USE_DOC_SKETCH: bool = True
    CONTEXTUAL_RETRIEVAL_DOC_SKETCH_CACHE_BACKEND: str = "redis"
    CONTEXTUAL_RETRIEVAL_DOC_SKETCH_CACHE_TTL_SECONDS: int = 3600
    # Redis key prefix for upload sketches; full key is {prefix}{tenant_id}:{content_sha256}
    CONTEXTUAL_RETRIEVAL_DOC_SKETCH_REDIS_KEY_PREFIX: str = "upload:doc_sketch:"
    CONTEXTUAL_RETRIEVAL_DOC_SKETCH_MAX_INPUT_CHARS: int = 12000
    CONTEXTUAL_RETRIEVAL_DOC_SKETCH_MAX_OUTPUT_TOKENS: int = 700
    CONTEXTUAL_RETRIEVAL_DOC_SKETCH_MAX_CHARS: int = 3500
    # Empty: use chunk_contextualization task model from factory (gpt-4o-mini by default)
    CONTEXTUAL_RETRIEVAL_DOC_SKETCH_MODEL: str = ""

    # Optional retrieval upgrades (production-gated)
    ENABLE_QUERY_DECOMPOSITION: bool = False
    # Log decomposition output in pipeline trace without mutating retrieval queries (staging).
    ENABLE_QUERY_DECOMPOSITION_SHADOW: bool = True
    QUERY_DECOMPOSITION_MAX_SUB_QUERIES: int = 4
    # Minimum query words for explanation-intent decomposition when intent routing is active.
    QUERY_DECOMPOSITION_MIN_QUERY_WORDS_EXPLANATION: int = 12
    ENABLE_CONTEXT_AWARE_RETRIEVAL_WEIGHTING: bool = True
    CONTEXT_AWARE_WEIGHTING_MAX_BOOST: float = 0.15
    # Below this intent confidence, retrieval uses neutral multipliers (legacy top_k * 3 behavior).
    RETRIEVAL_INTENT_ROUTING_MIN_CONFIDENCE: float = 0.55

    # Contextual BM25 + rank fusion (closest to Contextual Retrieval guide)
    ENABLE_BM25_RANK_FUSION: bool = True
    BM25_FUSION_TOP_K: int = 150  # candidate pool after fusion
    BM25_CORPUS_MAX_CHUNKS: int = 5000  # cap chunks fetched per request for BM25 corpus

    # ---------------------------
    # NCERT global knowledge (admin Pinecone namespace; separate from tenant chat embeddings)
    # ---------------------------
    NCERT_GLOBAL_PINECONE_NAMESPACE: str = "NcertDataGlobal"
    # Contextualization model for NCERT chunk enrichment (OpenAI chat model id).
    # Use a model your OpenAI account actually serves; override in .env when newer IDs ship.
    NCERT_GLOBAL_CONTEXT_MODEL: str = "gpt-4o-mini"
    # Embeddings for vectors stored under NCERT_GLOBAL_PINECONE_NAMESPACE — dimensions MUST match Pinecone index.
    NCERT_GLOBAL_EMBEDDING_MODEL: str = "text-embedding-3-large"
    NCERT_GLOBAL_EMBEDDING_DIMENSIONS: int = 1024
    # Max chunks to pull from global namespace per query before merge (cost/latency cap).
    NCERT_GLOBAL_RETRIEVAL_TOP_K: int = 24
    # Feature flag: merge NCERT global namespace into chat retrieval when client requests it.
    ENABLE_NCERT_GLOBAL_IN_CHAT: bool = True
    # Tutor mode: after retrieval, require semantic overlap between query and selected chunk text
    # before calling the answer LLM (blocks general-knowledge answers when NCERT context is off-topic).
    TUTOR_NCERT_RELEVANCE_GATE_ENABLED: bool = True
    # Max cosine similarity between query embedding and any selected chunk text embedding (same model).
    # Unrelated pairs (e.g. electrons vs temperature) typically sit well below ~0.30 with text-embedding-3-small.
    TUTOR_NCERT_MIN_CHUNK_RELEVANCE_COSINE: float = 0.34
    # When Tutor NCERT relevance gate is on, skip answer cache read/write so responses are always re-validated.
    TUTOR_NCERT_BYPASS_ANSWER_CACHE: bool = True

    # Normal chat: when the user explicitly selects one or more library sources, block answers that
    # are not grounded in retrieved chunk text (same embedding relevance idea as Tutor NCERT gate).
    CHAT_SELECTED_SOURCES_RELEVANCE_GATE_ENABLED: bool = True
    # Max hybrid/retrieval score (0–1) among chunks packed into the prompt; below this → LOW_SIMILARITY.
    CHAT_SELECTED_SOURCES_MIN_RETRIEVAL_SCORE: float = 0.30
    # Min cosine(query, chunk_text) for at least one selected chunk (tenant embedder).
    CHAT_SELECTED_SOURCES_MIN_CHUNK_RELEVANCE_COSINE: float = 0.34
    # When True, if relevance fails we still call the LLM with no document context (general answer)
    # and mark done_payload (answer_origin=global_only, GLOBAL_FALLBACK_USED).
    CHAT_ALLOW_GLOBAL_KNOWLEDGE_FALLBACK: bool = False
    # Skip answer cache for gated turns so stale ungrounded answers are not reused.
    CHAT_SELECTED_SOURCES_BYPASS_ANSWER_CACHE: bool = True

    # Strict RAG: after context is packed, require semantic + score (+ lexical) support before
    # calling the answer LLM. Prevents confident answers from model knowledge when chunks are weak/off-topic.
    CHAT_STRICT_CONTEXT_GROUNDING: bool = True
    CONTEXT_GROUNDING_MIN_COSINE: float = 0.40
    CONTEXT_GROUNDING_MIN_RETRIEVAL_SCORE: float = 0.28
    CONTEXT_GROUNDING_LEXICAL_ENABLED: bool = True
    CONTEXT_GROUNDING_LEXICAL_MIN_TERM_LEN: int = 3
    # Fraction of (capped) significant query terms that must appear in chunk text, unless cosine bypass fires.
    CONTEXT_GROUNDING_LEXICAL_MIN_TERM_FRACTION: float = 0.5
    CONTEXT_GROUNDING_LEXICAL_MAX_TERMS: int = 8
    # If max cosine meets this, skip lexical check (handles paraphrases without literal token overlap).
    CONTEXT_GROUNDING_LEXICAL_BYPASS_MIN_COSINE: float = 0.52

    # Central chat policy YAML (tone, rules, safety) injected into RAG system prompt
    ENABLE_CHAT_POLICY_YAML: bool = True
    CHAT_POLICY_YAML_PATH: str = ""  # empty = packages/core/prompts/policies/chat_policy.default.yaml

    # ---------------------------
    # Response Quality (single-pass, production-gated)
    # ---------------------------
    # Deterministic hallucination guard: scores whether high-risk sentences appear supported by retrieved context.
    # Off by default: the overlap-based retry often pushed the model to refuse even when chunks were relevant.
    ENABLE_HALLUCINATION_GUARD: bool = False
    HALLUCINATION_GUARD_MIN_SUPPORTED_RATIO: float = 0.65
    # Extra LLM call with "remove unsupported" — keep 0 unless you are debugging grounding only.
    HALLUCINATION_GUARD_MAX_RETRY: int = 0
    # Token overlap threshold per checked sentence. Higher => stricter.
    HALLUCINATION_GUARD_MIN_OVERLAP_SCORE: float = 0.22
    HALLUCINATION_GUARD_MIN_SENTENCE_CHARS: int = 28
    # When sentence overlap is low but many answer terms appear in context, treat as grounded (paraphrase).
    HALLUCINATION_GUARD_COARSE_RESCUE_ENABLED: bool = True
    HALLUCINATION_GUARD_COARSE_RECALL_MIN: float = 0.26
    # If True, replace answers that still fail the guard with "Not found..." (causes false refusals on paraphrase).
    HALLUCINATION_GUARD_FORCE_NOT_FOUND_ON_FAILURE: bool = False

    # Plan A: LlamaIndex RAG (ingestion + retrieval + synthesis)
    USE_LLAMA_INDEX_RAG: bool = True  # Feature flag: use LlamaIndex adapters for RAG
    
    # Phase 3: Output Token Optimization
    USE_OUTPUT_OPTIMIZATION: bool = True  # Enable Phase 3 output optimization
    ENFORCE_CITATIONS: bool = False  # Citations still retrieved server-side; UI hides them — avoid forcing [1] in text
    DEFAULT_OUTPUT_FORMAT: str = "paragraph"  # paragraph reads better for most Q&A; use bullets in-prose when listing
    USE_EARLY_STOP: bool = True  # Stop early after answering
    MAX_OUTPUT_TOKENS: Optional[int] = None  # Maximum output tokens (None = use CHAT_MAX_TOKENS)
    MAX_OUTPUT_CHARACTERS: Optional[int] = None  # Maximum output characters (None = no limit)
    MAX_OUTPUT_SENTENCES: Optional[int] = None  # Maximum output sentences (None = no limit) - removed limit for better completeness
    
    # Phase 4: Session Memory & Caching
    USE_SESSION_MEMORY: bool = True  # Enable Phase 4 session memory features
    ENABLE_RATE_LIMITING: bool = True  # Enable rate limiting and debounce
    ENABLE_ANSWER_CACHE: bool = True  # Enable answer caching for repeated queries
    ENABLE_CHAT_SUMMARIZATION: bool = True  # Enable periodic chat summarization
    ENABLE_MEMORY_PRUNING: bool = True  # Enable session memory pruning
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 30  # Max requests per minute per user
    RATE_LIMIT_DEBOUNCE_SECONDS: float = 2.0  # Debounce window (seconds)
    ANSWER_CACHE_TTL_SECONDS: int = 3600  # Answer cache TTL (1 hour)
    CHAT_SUMMARIZE_AFTER: int = 10  # Summarize when history exceeds this count
    CHAT_KEEP_RECENT: int = 5  # Keep last N messages unsummarized
    MAX_HISTORY_MESSAGES: int = 20  # Maximum messages in history
    MAX_HISTORY_TOKENS: int = 2000  # Maximum tokens for history
    MEMORY_PRUNING_STRATEGY: str = "recent"  # "recent", "relevance", "summary"
    
    # Phase 5: Security & Student Guardrails
    USE_SECURITY_GUARDRAILS: bool = True  # Enable Phase 5 security features
    ENABLE_SAFETY_FILTERS: bool = True  # Enable input/output moderation
    ENABLE_REFUSAL_TEMPLATES: bool = True  # Enable safe refusal responses
    ENABLE_INJECTION_DETECTION: bool = True  # Enable prompt injection detection
    # LLM intent classifier labels security_block → block before retrieval (few-shot in intent_classifier_system.j2).
    ENABLE_INTENT_SECURITY_BLOCK: bool = True
    ENABLE_SYLLABUS_LOCK: bool = False  # Enable syllabus-locked RAG (requires approved sources)
    ENABLE_INTENT_GATE: bool = True  # Enable academic-only intent enforcement
    ENABLE_PII_DETECTION: bool = True  # Enable PII detection and redaction
    # Injected into central chat policy YAML as age-appropriate guidance (k5 | 6-8 | 9-17 | adult). Default: ages 9–17.
    STUDENT_AGE_TIER: str = "9-17"
    SAFETY_STRICT_MODE: bool = True  # Strict safety filtering
    INJECTION_DETECTION_THRESHOLD: float = 0.6  # Prompt injection detection threshold
    # Second line of defense: cosine similarity vs paraphrased injection probes (OpenAI embeddings).
    ENABLE_PROMPT_INJECTION_EMBEDDING_SIM: bool = True
    PROMPT_INJECTION_EMBEDDING_SIM_THRESHOLD: float = 0.78
    PROMPT_INJECTION_EMBEDDING_FAIL_OPEN: bool = True  # On embedding errors, allow the request
    # After Jinja compilation: ensure grounding / context / policy sections are present before LLM call.
    ENABLE_PROMPT_INTEGRITY_CHECK: bool = True
    PROMPT_INJECTION_REFUSAL_MESSAGE: str = (
        "Your request contains instructions that are not allowed because they attempt to bypass "
        "the system's safety or source restrictions."
    )
    INTENT_ACADEMIC_THRESHOLD: float = 0.5  # Academic intent classification threshold
    APPROVED_SOURCE_IDS: str = ""  # Comma-separated list of approved source IDs for syllabus lock
    
    # Pipeline debug traces (LangGraph + RAG); in-memory ring buffer, dev-oriented
    ENABLE_PIPELINE_TRACE: bool = True
    PIPELINE_TRACE_MAX_STORED: int = 200
    PIPELINE_TRACE_SNIPPET_CHARS: int = 800
    PIPELINE_TRACE_VERBOSE: bool = False  # If True, allow longer prompt previews in traces (dev only)

    # Continuous Evaluation Loop
    ENABLE_EVALUATION: bool = True  # Enable continuous evaluation
    ENABLE_SCHEDULED_EVALS: bool = True  # Enable scheduled evaluations
    EVAL_INTERVAL_HOURS: int = 24  # Evaluation interval in hours
    ENABLE_COLD_START_HANDLING: bool = True  # Enable cold-start fallback logic
    ENABLE_CONFIDENCE_THRESHOLDING: bool = True  # Enable confidence scoring
    ENABLE_ANSWER_CONFIDENCE_THRESHOLDING: bool = True  # Enable LLM-based answer confidence gating
    CONFIDENCE_LOW_THRESHOLD: float = 0.5  # Low confidence threshold
    CONFIDENCE_HIGH_THRESHOLD: float = 0.7  # High confidence threshold
    ANSWER_CONFIDENCE_THRESHOLD: float = 0.6  # Threshold for showing answers based on LLM-evaluated confidence (lowered from 0.75 to be more lenient)
    TARGET_COST_REDUCTION_PERCENT: float = 50.0  # Target cost reduction (≥50%)
    TARGET_TOKEN_REDUCTION_PERCENT: float = 50.0  # Target token reduction (≥50%)
    
    # Pydantic v2 configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",  # Prevents extra env vars from causing errors
    )

    @field_validator("STUDENT_AGE_TIER", mode="before")
    @classmethod
    def _normalize_student_age_tier(cls, v: Any) -> str:
        if v is None or (isinstance(v, str) and not v.strip()):
            return "9-17"
        s = str(v).strip().lower()
        if s == "9-12":
            s = "9-17"
        allowed = {"k5", "6-8", "9-17", "adult"}
        return s if s in allowed else "9-17"


# Singleton instance of settings
settings = Settings()


