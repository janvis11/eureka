"""Tests for NvidiaProvider's NVIDIA-specific request shaping: disabling
Nemotron's default 'thinking' mode (which otherwise pollutes JSON output)
and passing input_type on embeddings."""

import pytest

from app.services.model_gateway.base import EmbeddingRequest, GenerationRequest, ChatMessage
from app.services.model_gateway.nvidia_provider import NvidiaProvider


class _FakeCompletions:
    def __init__(self):
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs

        class _Choice:
            class message:
                content = "ok"
        class _Usage:
            prompt_tokens = 1
            completion_tokens = 1
            total_tokens = 2
        class _Response:
            choices = [_Choice()]
            usage = _Usage()
        return _Response()


class _FakeEmbeddings:
    def __init__(self):
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs

        class _Item:
            embedding = [0.1, 0.2, 0.3]
        class _Response:
            data = [_Item() for _ in kwargs.get("input", [""])]
        return _Response()


class _FakeChat:
    def __init__(self):
        self.completions = _FakeCompletions()


class _FakeClient:
    def __init__(self):
        self.chat = _FakeChat()
        self.embeddings = _FakeEmbeddings()


def _make_provider():
    provider = NvidiaProvider.__new__(NvidiaProvider)
    provider._client = _FakeClient()
    provider._generation_model = "nvidia/nemotron-3-super-120b-a12b"
    provider._embedding_model = "nvidia/nemotron-3-embed-1b"
    return provider


@pytest.mark.asyncio
async def test_generate_disables_thinking_mode():
    provider = _make_provider()

    result = await provider.generate(
        GenerationRequest(messages=[ChatMessage(role="user", content="hi")])
    )

    kwargs = provider._client.chat.completions.last_kwargs
    assert kwargs["extra_body"]["chat_template_kwargs"]["enable_thinking"] is False
    assert result.text == "ok"


@pytest.mark.asyncio
async def test_generate_json_mode_sets_response_format():
    provider = _make_provider()

    await provider.generate(
        GenerationRequest(messages=[ChatMessage(role="user", content="hi")], json_mode=True)
    )

    kwargs = provider._client.chat.completions.last_kwargs
    assert kwargs["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_embed_passes_passage_input_type_for_documents():
    provider = _make_provider()

    await provider.embed(EmbeddingRequest(texts=["a doc"], purpose="document"))

    kwargs = provider._client.embeddings.last_kwargs
    assert kwargs["extra_body"]["input_type"] == "passage"


@pytest.mark.asyncio
async def test_embed_passes_query_input_type_for_queries():
    provider = _make_provider()

    await provider.embed(EmbeddingRequest(texts=["a query"], purpose="query"))

    kwargs = provider._client.embeddings.last_kwargs
    assert kwargs["extra_body"]["input_type"] == "query"
