"""
Application Configuration

Loads environment variables and provides settings for the application.
Uses Pydantic Settings for validation and type safety.

🔒 SINGLE SOURCE OF TRUTH for all config
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


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
    MAX_CONTEXT_CHUNKS: int = 10  # Maximum chunks for context selection
    MIN_CONTEXT_CHUNKS: int = 6  # Minimum chunks to ensure quality (guardrail)
    USE_LLM_RERANKING: bool = True  # Use LLM for reranking (more accurate but slower)
    RAG_DEBUG: bool = False  # Enable detailed debug logging for RAG pipeline
    QUERY_REWRITE_CONFIDENCE_THRESHOLD: float = 0.7  # Minimum confidence to use rewritten query
    CONTEXT_TOKEN_BUDGET: int = 4000  # Target token budget for context (approximate)
    
    # Pydantic v2 configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",  # Prevents extra env vars from causing errors
    )


# Singleton instance of settings
settings = Settings()


