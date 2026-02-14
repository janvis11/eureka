from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application settings."""
    
    # App
    APP_NAME: str = "Eureka AI"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./eureka.db")
    
    # Vector Store
    CHROMADB_PATH: str = os.getenv("CHROMADB_PATH", "./chromadb")
    
    # File Upload
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    
    # RAG Settings
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    # Use the sentence-transformers HF repo name for local embeddings
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # LLM Settings
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
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
    HF_API_TOKEN: str = os.getenv("HF_API_TOKEN", "")
    
    # Discovery Settings
    MAX_GAPS: int = 15
    MAX_HYPOTHESES_PER_RUN: int = 25
    TREND_WINDOW_DAYS: int = 365
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
