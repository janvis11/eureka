from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
from pydantic import field_validator
from urllib.parse import urlparse


class Settings(BaseSettings):
    """Application settings."""

    # App
    APP_NAME: str = "Eureka AI"
    DEBUG: bool = True

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

    # -----------------------------------------------------------------------
    # Model Gateway (provider-agnostic)
    # -----------------------------------------------------------------------
    # Which provider to use: groq, openai, ollama, fake, auto
    MODEL_PROVIDER: str = "auto"

    # Generation model (provider-specific model name)
    GENERATION_MODEL: str = "openai/gpt-oss-120b"

    # Embedding model (used by OpenAI-compatible embedding endpoint)
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Embedding dimension (must match the embedding model output)
    EMBEDDING_DIM: int = 384

    # Provider API keys (set whichever provider you use)
    GROQ_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None

    # OpenAI-compatible base URLs
    OPENAI_BASE_URL: Optional[str] = None
    EMBEDDING_BASE_URL: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"

    # Neo4j Configuration
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "eureka_password_change_me"
    NEO4J_DATABASE: str = "neo4j"

    # LLM Settings
    LLM_MODEL: str = "openai/gpt-oss-120b"  # Kept for backwards compat
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 1000

    # Discovery Settings
    MAX_GAPS: int = 15
    MAX_HYPOTHESES_PER_RUN: int = 25
    TREND_WINDOW_DAYS: int = 365

    # Security
    SECRET_KEY: str = "dev-secret-key-change-me"
    ALGORITHM: str = "HS256"

    # Optional legacy local-HF settings. HuggingFace is not required in the
    # production path; these exist only so older optional utilities can be
    # disabled cleanly.
    HF_USE_LOCAL_GENERATOR: bool = False
    DISCOVERY_MODEL: str = "google/flan-t5-small"

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
        debug_raw = os.environ.get("DEBUG", "true").lower()
        production_like = debug_raw in {"false", "0", "no", "production", "prod"}

        if not v or v in {
            "your-secret-key-change-in-production",
            "dev-secret-key-change-me",
            "change-this-in-production",
        }:
            if production_like:
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

    @field_validator("DEBUG", mode="before")
    @classmethod
    def normalize_debug(cls, v):
        """Accept common environment names accidentally supplied as DEBUG."""
        if isinstance(v, str):
            value = v.strip().lower()
            if value in {"release", "production", "prod"}:
                return False
            if value in {"debug", "development", "dev"}:
                return True
        return v

    @field_validator(
        "GROQ_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "OPENAI_BASE_URL",
        "EMBEDDING_BASE_URL",
        mode="before",
    )
    @classmethod
    def empty_str_to_none(cls, v):
        """Convert blank optional env vars to None."""
        if v is None:
            return None
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @field_validator("NEO4J_URI", mode="before")
    @classmethod
    def normalize_neo4j_uri(cls, v):
        """Normalize Neo4j URI and make Aura URIs secure by default."""
        if v is None:
            return v
        if not isinstance(v, str):
            return v

        cleaned = v.strip().strip('"').strip("'")
        if not cleaned:
            return "bolt://localhost:7687"

        parsed = urlparse(cleaned)
        host = (parsed.hostname or "").lower()
        if host.endswith(".databases.neo4j.io") and parsed.scheme in {"bolt", "neo4j"}:
            secure_scheme = "neo4j+s"
            netloc = parsed.netloc
            if "@" in netloc:
                auth, host_part = netloc.rsplit("@", 1)
                host_part = host_part.split(":", 1)[0]
                netloc = f"{auth}@{host_part}"
            else:
                netloc = host
            return f"{secure_scheme}://{netloc}"

        return cleaned

    @field_validator("NEO4J_USER", "NEO4J_PASSWORD", "NEO4J_DATABASE", mode="before")
    @classmethod
    def normalize_neo4j_strings(cls, v):
        """Trim accidental spaces/quotes in Neo4j env vars."""
        if v is None:
            return v
        if isinstance(v, str):
            return v.strip().strip('"').strip("'")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
