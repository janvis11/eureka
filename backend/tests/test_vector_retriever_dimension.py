"""Regression test: FAISS index dimension must track the active
embedding provider instead of silently mismatching."""

import numpy as np
import pytest

from app.services.model_gateway.base import EmbeddingRequest, EmbeddingResult
from app.services.retrieval.vector_retriever import VectorRetriever


class _FixedDimGateway:
    """Fake gateway returning embeddings of a fixed dimension."""

    def __init__(self, dim: int):
        self.dim = dim

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        rng = np.random.default_rng(42)
        vectors = rng.random((len(request.texts), self.dim)).tolist()
        return EmbeddingResult(embeddings=vectors, model="fake", dimension=self.dim)


def test_index_dimension_matches_configured_default():
    retriever = VectorRetriever(dimension=384, gateway=_FixedDimGateway(384))

    added = retriever.add_documents([{"text": "attention is all you need"}])

    assert added == 1
    assert retriever._index.d == 384


def test_index_self_heals_when_provider_dimension_changes():
    """If the embedding provider starts returning a different dimension
    (e.g. OpenAI text-embedding-3-small returning 1536 instead of the
    configured 384), the index must rebuild instead of crashing."""
    retriever = VectorRetriever(dimension=384, gateway=_FixedDimGateway(384))
    retriever.add_documents([{"text": "doc one"}, {"text": "doc two"}])
    assert retriever._index.d == 384
    assert retriever._index.ntotal == 2

    # Provider switches to returning 1536-dim vectors mid-run.
    retriever._gateway = _FixedDimGateway(1536)
    retriever.add_documents([{"text": "doc three"}])

    assert retriever._index.d == 1536
    assert retriever.dimension == 1536
    # Previously stored docs were re-embedded and preserved, plus the new one.
    assert retriever._index.ntotal == 3
    assert len(retriever._doc_store) == 3


def test_search_returns_empty_instead_of_crashing_on_dim_mismatch():
    retriever = VectorRetriever(dimension=384, gateway=_FixedDimGateway(384))
    retriever.add_documents([{"text": "doc one"}])

    # Simulate a query embedded by a provider returning a different dimension
    # than the index was built with (should never crash faiss.search).
    retriever._gateway = _FixedDimGateway(1536)
    results = retriever.search("doc one", top_k=5)

    assert results == []
