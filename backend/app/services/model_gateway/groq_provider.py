"""Groq provider for the model gateway.

Uses Groq's OpenAI-compatible API for generation.
For embeddings, falls back to a lightweight local approach or raises
an error if no embedding provider is configured.
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
from app.services.model_gateway.local_embeddings import embed_texts

logger = logging.getLogger(__name__)


class GroqProvider:
    """Groq LLM provider — generation via Groq API, embeddings via OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str,
        generation_model: str = "openai/gpt-oss-120b",
        embedding_api_key: Optional[str] = None,
        embedding_model: str = "text-embedding-3-small",
        embedding_base_url: Optional[str] = None,
    ):
        from groq import Groq

        self._client = Groq(api_key=api_key)
        self._generation_model = generation_model

        # Groq doesn't offer embeddings natively — use OpenAI-compatible
        # endpoint if provided, or a local fallback
        self._embedding_model = embedding_model
        self._embedding_client = None
        if embedding_api_key:
            try:
                from openai import OpenAI
                kwargs = {"api_key": embedding_api_key}
                if embedding_base_url:
                    kwargs["base_url"] = embedding_base_url
                self._embedding_client = OpenAI(**kwargs)
            except ImportError:
                logger.warning("openai package not installed — embeddings unavailable via OpenAI")
        
        # Local embedding fallback (sentence-transformers if available)
        self._local_embedder = None

        logger.info(
            f"GroqProvider initialized: generation={self._generation_model}"
        )

    def _ensure_local_embedder(self):
        """Lazily initialize optional SentenceTransformer fallback."""
        if self._local_embedder is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
            self._local_embedder = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Local SentenceTransformer loaded as embedding fallback")
        except ImportError:
            logger.warning(
                "sentence-transformers not available; using local lexical "
                "hash embeddings as the offline fallback."
            )
            self._local_embedder = False  # Mark as permanently unavailable
        except Exception as e:
            logger.warning(
                "SentenceTransformer embedding fallback could not start; "
                f"using local lexical hash embeddings instead: {e}"
            )
            self._local_embedder = False

    # -----------------------------------------------------------------------
    # Generation
    # -----------------------------------------------------------------------
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate text using Groq API."""
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
        """Embed texts using OpenAI-compatible API or local fallback."""
        # Try OpenAI-compatible endpoint first
        if self._embedding_client:
            try:
                return await self._embed_openai(request)
            except Exception as e:
                logger.warning(
                    "OpenAI-compatible embeddings failed; switching to local "
                    f"embedding fallback for this process: {e}"
                )
                self._embedding_client = None

        # Try local fallback
        self._ensure_local_embedder()
        if self._local_embedder and self._local_embedder is not False:
            return self._embed_local(request)

        return self._embed_local_hash(request)

    async def _embed_openai(self, request: EmbeddingRequest) -> EmbeddingResult:
        """Embed via OpenAI-compatible API.

        text-embedding-3-* models return 1536 dims unless `dimensions` is
        passed explicitly, which would silently mismatch the FAISS index
        built at the configured EMBEDDING_DIM.
        """
        kwargs = {"model": self._embedding_model, "input": request.texts}
        if self._embedding_model.startswith("text-embedding-3"):
            kwargs["dimensions"] = get_settings().EMBEDDING_DIM

        response = self._embedding_client.embeddings.create(**kwargs)
        embeddings = [item.embedding for item in response.data]
        dim = len(embeddings[0]) if embeddings else 0
        return EmbeddingResult(
            embeddings=embeddings,
            model=self._embedding_model,
            dimension=dim,
        )

    def _embed_local(self, request: EmbeddingRequest) -> EmbeddingResult:
        """Embed via local SentenceTransformer."""
        embeddings_np = self._local_embedder.encode(
            request.texts,
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        embeddings = embeddings_np.tolist()
        dim = len(embeddings[0]) if embeddings else 0
        return EmbeddingResult(
            embeddings=embeddings,
            model="all-MiniLM-L6-v2",
            dimension=dim,
        )

    def _embed_local_hash(self, request: EmbeddingRequest) -> EmbeddingResult:
        """Embed via deterministic local lexical hashing."""
        dimension = get_settings().EMBEDDING_DIM
        embeddings = embed_texts(request.texts, dimension=dimension)
        return EmbeddingResult(
            embeddings=embeddings,
            model="local-lexical-hash-v1",
            dimension=dimension,
        )

    # -----------------------------------------------------------------------
    # Reranking (not supported by Groq — passthrough)
    # -----------------------------------------------------------------------
    async def rerank(
        self, query: str, documents: List[str], top_k: int = 10
    ) -> List[RerankResult]:
        """Reranking not available via Groq — return original order."""
        return [
            RerankResult(index=i, score=1.0 / (i + 1), text=doc)
            for i, doc in enumerate(documents[:top_k])
        ]
