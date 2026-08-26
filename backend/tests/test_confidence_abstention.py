"""Tests for the abstention gate: the RAG path must refuse to answer when
retrieval evidence is weak, instead of asking the LLM to produce a
fluent-sounding answer from nothing."""

import pytest

from app.services.retrieval.confidence import compute_confidence
from app.services.rag_engine import RAGEngine
from app.services.model_gateway.base import GenerationResult


def _chunk(distance, document_id="doc-1", text="some evidence"):
    return {"text": text, "distance": distance, "metadata": {"document_id": document_id}}


def test_no_context_abstains():
    result = compute_confidence([])
    assert result.should_answer is False
    assert result.reason == "no_evidence_retrieved"


def test_strong_single_source_evidence_answers():
    context = [_chunk(distance=5), _chunk(distance=8), _chunk(distance=10)]
    result = compute_confidence(context)
    assert result.should_answer is True
    assert result.score > 0.35


def test_weak_distant_matches_abstain():
    context = [_chunk(distance=90), _chunk(distance=95)]
    result = compute_confidence(context)
    assert result.should_answer is False
    assert result.reason == "insufficient_evidence"
    assert "abstain" not in (result.what_would_help or "")  # message should be actionable, not just a label
    assert result.what_would_help


def test_source_diversity_raises_confidence():
    single_source = [_chunk(distance=40, document_id="doc-1") for _ in range(3)]
    multi_source = [_chunk(distance=40, document_id=f"doc-{i}") for i in range(3)]

    single_result = compute_confidence(single_source)
    multi_result = compute_confidence(multi_source)

    assert multi_result.score > single_result.score


class _FixedAnswerGateway:
    async def generate(self, request):
        return GenerationResult(text="Here is the answer.", model="fake")

    async def embed(self, request):
        raise AssertionError("embed should not be called by generate_answer")


@pytest.mark.asyncio
async def test_generate_answer_abstains_on_weak_context(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMADB_PATH", str(tmp_path))
    from app.config import get_settings
    get_settings.cache_clear()

    engine = RAGEngine(gateway=_FixedAnswerGateway())
    weak_context = [_chunk(distance=95), _chunk(distance=98)]

    result = await engine.generate_answer("What causes X?", weak_context)

    assert result["abstained"] is True
    assert result["reason"] == "insufficient_evidence"
    assert "closest_evidence" in result
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_generate_answer_answers_on_strong_context(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMADB_PATH", str(tmp_path))
    from app.config import get_settings
    get_settings.cache_clear()

    engine = RAGEngine(gateway=_FixedAnswerGateway())
    strong_context = [_chunk(distance=5), _chunk(distance=8, document_id="doc-2")]

    result = await engine.generate_answer("What causes X?", strong_context)

    assert result["abstained"] is False
    assert result["answer"] == "Here is the answer."
    get_settings.cache_clear()
