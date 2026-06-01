"""Factory for creating model gateway instances."""

from __future__ import annotations

import logging
from typing import Optional

from app.services.model_gateway.base import ModelGateway

logger = logging.getLogger(__name__)


def create_gateway(provider: Optional[str] = None) -> ModelGateway:
    """Create a ModelGateway based on config or explicit provider name.

    Provider resolution order:
        1. Explicit `provider` argument
        2. `MODEL_PROVIDER` from settings
        3. Auto-detect from available API keys
        4. Fall back to 'fake' provider
    """
    from app.config import get_settings

    settings = get_settings()
    provider = (provider or getattr(settings, "MODEL_PROVIDER", "") or "").lower().strip()

    # Auto-detect if provider not set
    if not provider or provider == "auto":
        if getattr(settings, "GROQ_API_KEY", None):
            provider = "groq"
        elif getattr(settings, "OPENAI_API_KEY", None):
            provider = "openai"
        elif getattr(settings, "ANTHROPIC_API_KEY", None):
            provider = "anthropic"
        elif getattr(settings, "GEMINI_API_KEY", None):
            provider = "gemini"
        else:
            logger.warning(
                "No API keys found — falling back to fake provider. "
                "Set GROQ_API_KEY, OPENAI_API_KEY, etc. in your .env file."
            )
            provider = "fake"

    logger.info(f"Creating model gateway: provider={provider}")

    if provider == "groq":
        from app.services.model_gateway.groq_provider import GroqProvider

        return GroqProvider(
            api_key=settings.GROQ_API_KEY,
            generation_model=getattr(settings, "GENERATION_MODEL", "openai/gpt-oss-120b"),
            embedding_api_key=getattr(settings, "OPENAI_API_KEY", None),
            embedding_model=getattr(settings, "EMBEDDING_MODEL", "text-embedding-3-small"),
            embedding_base_url=getattr(settings, "EMBEDDING_BASE_URL", None),
        )

    elif provider == "openai":
        # OpenAI-compatible provider (also covers Ollama via base_url)
        from app.services.model_gateway.groq_provider import GroqProvider  # reuse OpenAI-compat shape

        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("Install 'openai' package: pip install openai")

        # We build a thin wrapper using the Groq provider structure
        # since Groq's API is OpenAI-compatible
        from app.services.model_gateway.openai_provider import OpenAIProvider

        return OpenAIProvider(
            api_key=settings.OPENAI_API_KEY,
            generation_model=getattr(settings, "GENERATION_MODEL", "gpt-4.1"),
            embedding_model=getattr(settings, "EMBEDDING_MODEL", "text-embedding-3-small"),
            base_url=getattr(settings, "OPENAI_BASE_URL", None),
        )

    elif provider == "ollama":
        from app.services.model_gateway.openai_provider import OpenAIProvider

        return OpenAIProvider(
            api_key="ollama",  # Ollama doesn't need a real key
            generation_model=getattr(settings, "GENERATION_MODEL", "llama3.1"),
            embedding_model=getattr(settings, "EMBEDDING_MODEL", "nomic-embed-text"),
            base_url=getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        )

    elif provider == "fake":
        from app.services.model_gateway.fake_provider import FakeProvider

        return FakeProvider()

    else:
        raise ValueError(
            f"Unknown model provider: '{provider}'. "
            f"Supported: groq, openai, ollama, fake"
        )
