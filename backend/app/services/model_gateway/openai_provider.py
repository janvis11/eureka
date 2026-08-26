"""OpenAI-compatible provider for the model gateway.

Works with OpenAI, Azure OpenAI, Ollama, and any OpenAI-compatible API.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from app.config import get_settings
from app.services.model_gateway.base import (
    EmbeddingRequest,
    EmbeddingResult,
    GenerationRequest,
    GenerationResult,
    RerankResult,
)

logger = logging.getLogger(__name__)


class OpenAIProvider:
    """Provider using OpenAI-compatible APIs for generation and embeddings."""

    def __init__(
        self,
        api_key: str,
        generation_model: str = "gpt-4.1",
        embedding_model: str = "text-embedding-3-small",
        base_url: Optional[str] = None,
    ):
        from openai import OpenAI

        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url

        self._client = OpenAI(**kwargs)
        self._generation_model = generation_model
        self._embedding_model = embedding_model

        logger.info(
            f"OpenAIProvider initialized: generation={generation_model}, "
            f"embedding={embedding_model}, base_url={base_url or 'default'}"
        )

    # -----------------------------------------------------------------------
    # Generation
    # -----------------------------------------------------------------------
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate text using OpenAI-compatible chat completions."""
        messages = [
            {"role": m.role, "content": m.content} for m in request.messages
        ]
        kwargs = {
            "model": self._generation_model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = self._client.chat.completions.create(**kwargs)

        text = response.choices[0].message.content or ""
        usage = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        return GenerationResult(
            text=text,
            model=self._generation_model,
            usage=usage,
        )

    # -----------------------------------------------------------------------
    # Embeddings
    # -----------------------------------------------------------------------
    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        """Embed texts using OpenAI-compatible embeddings endpoint.

        text-embedding-3-* models support a `dimensions` param that truncates
        the output to the configured EMBEDDING_DIM. Without it, these models
        always return 1536 dims regardless of what the FAISS index was built
        for, silently corrupting retrieval the moment this provider is used.
        """
        kwargs = {"model": self._embedding_model, "input": request.texts}
        if self._embedding_model.startswith("text-embedding-3"):
            kwargs["dimensions"] = get_settings().EMBEDDING_DIM

        response = self._client.embeddings.create(**kwargs)
        embeddings = [item.embedding for item in response.data]
        dim = len(embeddings[0]) if embeddings else 0

        return EmbeddingResult(
            embeddings=embeddings,
            model=self._embedding_model,
            dimension=dim,
        )

    # -----------------------------------------------------------------------
    # Reranking (not natively supported — passthrough)
    # -----------------------------------------------------------------------
    async def rerank(
        self, query: str, documents: List[str], top_k: int = 10
    ) -> List[RerankResult]:
        """Reranking not available — return original order."""
        return [
            RerankResult(index=i, score=1.0 / (i + 1), text=doc)
            for i, doc in enumerate(documents[:top_k])
        ]
