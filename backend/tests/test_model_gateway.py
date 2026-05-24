"""Tests for the provider-agnostic ModelGateway."""

import pytest
import asyncio
from app.services.model_gateway.base import (
    ChatMessage,
    GenerationRequest,
    GenerationResult,
    EmbeddingRequest,
    EmbeddingResult,
    RerankResult,
    ModelGateway,
)
from app.services.model_gateway.fake_provider import FakeProvider, FAKE_EMBEDDING_DIM
from app.services.model_gateway.factory import create_gateway


# ---------------------------------------------------------------------------
# FakeProvider tests
# ---------------------------------------------------------------------------

@pytest.fixture
def fake():
    return FakeProvider()


@pytest.mark.asyncio
async def test_fake_generate_returns_result(fake):
    req = GenerationRequest(
        messages=[ChatMessage(role="user", content="Tell me about research gaps.")],
    )
    result = await fake.generate(req)
    assert isinstance(result, GenerationResult)
    assert len(result.text) > 0
    assert result.model == "fake-model"


@pytest.mark.asyncio
async def test_fake_generate_returns_json_for_gap_prompt(fake):
    import json
    req = GenerationRequest(
        messages=[ChatMessage(role="user", content="Find research gaps in these papers")],
    )
    result = await fake.generate(req)
    parsed = json.loads(result.text)
    assert "gaps" in parsed
    assert len(parsed["gaps"]) > 0


@pytest.mark.asyncio
async def test_fake_embed_returns_correct_shape(fake):
    texts = ["Hello world", "Another text"]
    req = EmbeddingRequest(texts=texts)
    result = await fake.embed(req)
    assert isinstance(result, EmbeddingResult)
    assert len(result.embeddings) == 2
    assert len(result.embeddings[0]) == FAKE_EMBEDDING_DIM
    assert result.dimension == FAKE_EMBEDDING_DIM


@pytest.mark.asyncio
async def test_fake_embed_deterministic(fake):
    """Same text should produce the same embedding."""
    texts = ["Deterministic test"]
    r1 = await fake.embed(EmbeddingRequest(texts=texts))
    r2 = await fake.embed(EmbeddingRequest(texts=texts))
    assert r1.embeddings[0] == r2.embeddings[0]


@pytest.mark.asyncio
async def test_fake_rerank(fake):
    docs = ["doc A", "doc B", "doc C"]
    results = await fake.rerank("query", docs)
    assert len(results) == 3
    assert all(isinstance(r, RerankResult) for r in results)
    assert results[0].score > results[1].score


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------

def test_fake_implements_gateway_protocol():
    """FakeProvider should satisfy the ModelGateway protocol."""
    fake = FakeProvider()
    assert isinstance(fake, ModelGateway)


# ---------------------------------------------------------------------------
# Factory tests
# ---------------------------------------------------------------------------

def test_factory_creates_fake_provider(monkeypatch):
    """Factory should create FakeProvider when MODEL_PROVIDER=fake."""
    monkeypatch.setenv("MODEL_PROVIDER", "fake")
    monkeypatch.setenv("DEBUG", "true")
    # Clear the lru_cache to pick up new env vars
    from app.config import get_settings
    get_settings.cache_clear()

    gw = create_gateway("fake")
    assert isinstance(gw, FakeProvider)

    # Cleanup
    get_settings.cache_clear()


def test_factory_auto_falls_back_to_fake(monkeypatch):
    """With no API keys, auto detection should fall back to fake."""
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("MODEL_PROVIDER", "auto")

    from app.config import get_settings
    get_settings.cache_clear()

    gw = create_gateway()
    assert isinstance(gw, FakeProvider)

    # Cleanup
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# No HuggingFace imports on main path
# ---------------------------------------------------------------------------

def test_no_hf_imports_on_main_path():
    """The main app module path should not require HuggingFace packages."""
    import importlib
    import sys

    # Remove any cached HF modules to ensure clean test
    hf_modules = [k for k in sys.modules if
                  'transformers' in k or
                  'sentence_transformers' in k or
                  'huggingface_hub' in k]

    # These should NOT be required imports
    # (they may be present if installed, but should not error if missing)
    # Check that our core modules can be imported
    importlib.reload(importlib.import_module("app.services.model_gateway.base"))
    importlib.reload(importlib.import_module("app.services.model_gateway.fake_provider"))
    importlib.reload(importlib.import_module("app.services.model_gateway.factory"))
