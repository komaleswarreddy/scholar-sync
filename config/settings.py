"""
Application Configuration

Loads environment variables and provides settings for the application.
Uses Pydantic Settings for validation and type safety.

🔒 SINGLE SOURCE OF TRUTH for all config
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""    

    # App
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"
    
    # Database
    DATABASE_URL: str = Field(..., description="PostgreSQL database connection string (required)")
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    
    # Vector Database
    PINECONE_API_KEY: str = ""
    PINECONE_ENVIRONMENT: str = "us-east-1"
    PINECONE_INDEX_NAME: str = "scholarsync-vectors"
    
    # LLM APIs
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    
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
    TOP_K_CHUNKS: int = 10
    SIMILARITY_THRESHOLD: float = 0.7
    CHAT_MAX_TOKENS: int = 2048  # Maximum tokens for chat responses
    
    # Phase 2: Retrieval Quality & Cost Guardrails
    USE_RETRIEVAL_AGENTS: bool = True  # Enable Phase 2 agents
    MMR_LAMBDA: float = 0.7  # MMR balance (0.0=diversity, 1.0=relevance)
    HYBRID_VECTOR_WEIGHT: float = 0.7  # Hybrid retrieval vector weight
    HYBRID_KEYWORD_WEIGHT: float = 0.3  # Hybrid retrieval keyword weight
    MAX_CONTEXT_CHUNKS: int = 8  # Maximum chunks for context selection (reduced from 10)
    MIN_CONTEXT_CHUNKS: int = 4  # Minimum chunks to ensure quality (reduced from 6)
    USE_LLM_RERANKING: bool = True  # Use LLM for reranking (more accurate but slower)
    RAG_DEBUG: bool = False  # Enable detailed debug logging for RAG pipeline
    QUERY_REWRITE_CONFIDENCE_THRESHOLD: float = 0.7  # Minimum confidence to use rewritten query
    CONTEXT_TOKEN_BUDGET: int = 2500  # Target token budget for context (reduced from 4000)
    MAX_CHUNK_LENGTH: int = 500  # Maximum characters per chunk in context (truncate if longer)
    USE_CHUNK_COMPRESSION: bool = True  # Compress lower-scoring chunks to reduce tokens
    
    # Phase 3: Output Token Optimization
    USE_OUTPUT_OPTIMIZATION: bool = True  # Enable Phase 3 output optimization
    ENFORCE_CITATIONS: bool = True  # Enforce citations for all claims
    DEFAULT_OUTPUT_FORMAT: str = "bullet_points"  # bullet_points, numbered_list, paragraph, structured
    USE_EARLY_STOP: bool = True  # Stop early after answering
    MAX_OUTPUT_TOKENS: Optional[int] = None  # Maximum output tokens (None = use CHAT_MAX_TOKENS)
    MAX_OUTPUT_CHARACTERS: Optional[int] = None  # Maximum output characters (None = no limit)
    MAX_OUTPUT_SENTENCES: Optional[int] = 10  # Maximum output sentences (None = no limit)
    
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
    ENABLE_SYLLABUS_LOCK: bool = False  # Enable syllabus-locked RAG (requires approved sources)
    ENABLE_INTENT_GATE: bool = True  # Enable academic-only intent enforcement
    ENABLE_PII_DETECTION: bool = True  # Enable PII detection and redaction
    SAFETY_STRICT_MODE: bool = True  # Strict safety filtering
    INJECTION_DETECTION_THRESHOLD: float = 0.6  # Prompt injection detection threshold
    INTENT_ACADEMIC_THRESHOLD: float = 0.5  # Academic intent classification threshold
    APPROVED_SOURCE_IDS: str = ""  # Comma-separated list of approved source IDs for syllabus lock
    
    # Pydantic v2 configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",  # Prevents extra env vars from causing errors
    )


# Singleton instance of settings
settings = Settings()


