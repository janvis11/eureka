"""NVIDIA NIM provider for the model gateway.

Uses NVIDIA's hosted, OpenAI-compatible inference API
(https://integrate.api.nvidia.com/v1) for generation and embeddings.

Quirks specific to this provider that the OpenAI-compatible base pattern
doesn't cover (verified against the live API):
- Nemotron 3 models have "thinking" (reasoning trace) ON by default, which
  pollutes JSON-mode output unless explicitly disabled per request.
- Embedding models expect an `input_type` of "query" or "passage" (NVIDIA's
  retrieval convention), not just raw text.
- `nemotron-3-embed-1b` only accepts its native 2048-dim output — unlike
  OpenAI's text-embedding-3-*, there's no `dimensions` truncation param.
- NVIDIA's own docs recommend `guided_json` (a JSON-schema-constrained
  decode) over plain `response_format={"type": "json_object"}`, since the
  latter permits any valid JSON including `{}`. This provider still uses
  plain json_mode for now — adopting guided_json needs each caller to
  supply a schema, which is a larger change. See docs/LIMITATIONS.md.
"""

from __future__ import annotations

import logging
from typing import List

from app.services.model_gateway.base import (
    EmbeddingRequest,
    EmbeddingResult,
    GenerationRequest,
    GenerationResult,
    RerankResult,
)
from app.services.model_gateway.retry import retry_llm_call

logger = logging.getLogger(__name__)


class NvidiaProvider:
    """Provider using NVIDIA NIM's OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str,
        generation_model: str = "nvidia/nemotron-3-super-120b-a12b",
        embedding_model: str = "nvidia/nemotron-3-embed-1b",
        base_url: str = "https://integrate.api.nvidia.com/v1",
    ):
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._generation_model = generation_model
        self._embedding_model = embedding_model

        logger.info(
            f"NvidiaProvider initialized: generation={generation_model}, "
            f"embedding={embedding_model}, base_url={base_url}"
        )

    # -----------------------------------------------------------------------
    # Generation
    # -----------------------------------------------------------------------
    @retry_llm_call
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate text using NVIDIA NIM chat completions."""
        messages = [
            {"role": m.role, "content": m.content} for m in request.messages
        ]
        kwargs = {
            "model": self._generation_model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            # Nemotron 3 reasoning is on by default and emits a thinking
            # trace before the actual content, which breaks JSON parsing
            # and wastes tokens on prompts that don't need it.
            "extra_body": {"chat_template_kwargs": {"enable_thinking": False}},
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
    @retry_llm_call
    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        """Embed texts using NVIDIA NIM's embeddings endpoint.

        NVIDIA's retrieval-tuned embedding models score higher when told
        whether the text being embedded is a search query or a document to
        be searched over — passed via `input_type`, not a standard OpenAI
        field.
        """
        input_type = "query" if request.purpose == "query" else "passage"
        response = self._client.embeddings.create(
            model=self._embedding_model,
            input=request.texts,
            extra_body={"input_type": input_type},
        )
        embeddings = [item.embedding for item in response.data]
        dim = len(embeddings[0]) if embeddings else 0

        return EmbeddingResult(
            embeddings=embeddings,
            model=self._embedding_model,
            dimension=dim,
        )

    # -----------------------------------------------------------------------
    # Reranking (not exposed through this endpoint — passthrough)
    # -----------------------------------------------------------------------
    async def rerank(
        self, query: str, documents: List[str], top_k: int = 10
    ) -> List[RerankResult]:
        """Reranking not available — return original order."""
        return [
            RerankResult(index=i, score=1.0 / (i + 1), text=doc)
            for i, doc in enumerate(documents[:top_k])
        ]
