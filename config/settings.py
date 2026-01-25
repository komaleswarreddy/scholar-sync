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
    CHUNK_OVERLAP: int = 200
    
    # RAG Configuration
    TOP_K_CHUNKS: int = 10
    SIMILARITY_THRESHOLD: float = 0.7
    
    # Pydantic v2 configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",  # Prevents extra env vars from causing errors
    )


# Singleton instance of settings
settings = Settings()


