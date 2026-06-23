import pytest

from app.services.model_gateway.base import EmbeddingRequest
from app.services.model_gateway.local_embeddings import embed_texts


def test_local_hash_embeddings_rank_lexical_matches_higher():
    query, relevant, unrelated = embed_texts([
        "what is attention",
        "Scaled dot product attention computes weights over values from queries and keys.",
        "The experiment measures fertilizer response in wheat fields.",
    ])

    def dot(a, b):
        return sum(x * y for x, y in zip(a, b))

    assert dot(query, relevant) > dot(query, unrelated)


@pytest.mark.asyncio
async def test_groq_embeddings_fall_back_when_api_embeddings_fail(monkeypatch):
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("EMBEDDING_DIM", "384")

    from app.config import get_settings
    from app.services.model_gateway.groq_provider import GroqProvider

    get_settings.cache_clear()

    class BrokenEmbeddings:
        def create(self, **kwargs):
            raise RuntimeError("insufficient_quota")

    class BrokenClient:
        embeddings = BrokenEmbeddings()

    provider = GroqProvider.__new__(GroqProvider)
    provider._embedding_model = "text-embedding-3-small"
    provider._embedding_client = BrokenClient()
    provider._local_embedder = False

    result = await GroqProvider.embed(
        provider,
        EmbeddingRequest(texts=["attention mechanism"], purpose="document"),
    )

    assert result.model == "local-lexical-hash-v1"
    assert result.dimension == 384
    assert len(result.embeddings) == 1
    assert provider._embedding_client is None

    get_settings.cache_clear()
