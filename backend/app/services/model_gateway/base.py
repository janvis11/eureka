"""Base interfaces for provider-agnostic model gateway.

All providers must implement the ModelGateway protocol.
"""

from __future__ import annotations

from typing import List, Literal, Optional, Protocol, runtime_checkable

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    """A single chat message."""
    role: Literal["system", "user", "assistant"] = "user"
    content: str


class GenerationRequest(BaseModel):
    """Request payload for text generation."""
    messages: List[ChatMessage]
    temperature: float = 0.2
    max_tokens: int = 1200
    json_mode: bool = False


class GenerationResult(BaseModel):
    """Result from generation call."""
    text: str
    model: str = ""
    usage: dict = Field(default_factory=dict)


class EmbeddingRequest(BaseModel):
    """Request payload for embedding texts."""
    texts: List[str]
    purpose: Literal["document", "query"] = "document"


class EmbeddingResult(BaseModel):
    """Result from embedding call."""
    embeddings: List[List[float]]
    model: str = ""
    dimension: int = 0


class RerankResult(BaseModel):
    """A single reranked document."""
    index: int
    score: float
    text: str = ""


# ---------------------------------------------------------------------------
# Gateway protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class ModelGateway(Protocol):
    """Protocol that every model provider must satisfy."""

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate text from messages."""
        ...

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        """Embed a list of texts."""
        ...

    async def rerank(
        self, query: str, documents: List[str], top_k: int = 10
    ) -> List[RerankResult]:
        """Rerank documents by relevance to query.

        Optional — providers that do not support reranking should return
        documents in their original order with uniform scores.
        """
        ...
