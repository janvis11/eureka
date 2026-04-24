from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings."""

    # App
    APP_NAME: str = "Eureka AI"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "sqlite:///./eureka.db"

    # Vector Store
    CHROMADB_PATH: str = "./chromadb"

    # File Upload
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB

    # RAG Settings
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    # Use the sentence-transformers HF repo name for local embeddings
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # LLM Settings
    GROQ_API_KEY: Optional[str] = None
    LLM_MODEL: str = "llama-3.1-70b-versatile"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 1000

    # Hugging Face local models for cost-free tasks (embeddings/discovery/keywords)
    # These are open-source, CPU-friendly models you can run locally.
    DISCOVERY_MODEL: str = "google/flan-t5-small"
    KEYWORD_MODEL: str = "google/flan-t5-small"
    # Toggle to use local HF models for generation (discovery/keywords)
    HF_USE_LOCAL_GENERATOR: bool = True
    # Optional: HuggingFace API token for Inference API
    HF_API_TOKEN: Optional[str] = None

    # Discovery Settings
    MAX_GAPS: int = 15
    MAX_HYPOTHESES_PER_RUN: int = 25
    TREND_WINDOW_DAYS: int = 365
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"

    # CORS and Host restrictions
    ALLOWED_ORIGINS: str = "*"  # Comma-separated list of allowed origins
    ALLOWED_HOSTS: str = "*"    # Comma-separated list of allowed hosts

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_PER_HOUR: int = 1000

    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def validate_secret_key(cls, v):
        """Ensure SECRET_KEY is set and sufficiently random for production."""
        import os
        # Check if running in production (DEBUG=False)
        debug_mode = os.environ.get("DEBUG", "false").lower() == "true"

        if not v or v == "your-secret-key-change-in-production":
            if not debug_mode:
                # In production, raise an error if SECRET_KEY is not properly set
                raise ValueError(
                    "SECRET_KEY is not set or using default value. "
                    "Generate a secure key: python -c 'import secrets; print(secrets.token_urlsafe(32))' "
                    "and set it in your .env file or environment variables."
                )
            # Development fallback - generate random key with warning
            import secrets
            return secrets.token_urlsafe(32)
        return v

    @field_validator("HF_API_TOKEN", "GROQ_API_KEY", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        """Convert empty strings to None for optional fields."""
        if v is None or v == "":
            return None
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
