"""Provider-agnostic model gateway for Eureka.

Usage:
    from app.services.model_gateway import create_gateway, ModelGateway
    gateway = create_gateway()  # reads config
    result = await gateway.generate(GenerationRequest(...))
    result = await gateway.embed(EmbeddingRequest(...))
"""

from app.services.model_gateway.base import (
    ChatMessage,
    GenerationRequest,
    GenerationResult,
    EmbeddingRequest,
    EmbeddingResult,
    RerankResult,
    ModelGateway,
)
from app.services.model_gateway.factory import create_gateway

__all__ = [
    "ChatMessage",
    "GenerationRequest",
    "GenerationResult",
    "EmbeddingRequest",
    "EmbeddingResult",
    "RerankResult",
    "ModelGateway",
    "create_gateway",
]
