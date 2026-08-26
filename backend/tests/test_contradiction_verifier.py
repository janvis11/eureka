"""Tests for the two-stage contradiction detector: the antonym miner is a
high-recall candidate generator, the LLM verifier is the high-precision
filter that tells genuine contradictions apart from context differences."""

import json

import pytest

from app.services.discovery.contradiction_verifier import ContradictionVerifier
from app.services.model_gateway.base import GenerationResult


class _ScriptedGateway:
    """Returns queued JSON responses in order, one per generate() call."""

    def __init__(self, responses):
        self._responses = list(responses)

    async def generate(self, request):
        payload = self._responses.pop(0)
        return GenerationResult(text=json.dumps(payload), model="fake")


class _BrokenGateway:
    async def generate(self, request):
        raise RuntimeError("provider unavailable")


CANDIDATE = {
    "entity": "metformin",
    "claim_a_text": "Metformin improves insulin sensitivity in adults with type 2 diabetes.",
    "claim_b_text": "Metformin reduces insulin sensitivity in pediatric patients.",
}


@pytest.mark.asyncio
async def test_true_contradiction_is_confirmed():
    verifier = ContradictionVerifier(gateway=_ScriptedGateway([
        {"verdict": "CONTRADICTION", "differing_condition": None, "reasoning": "Same population, opposite effect."},
    ]))

    result = await verifier.verify(CANDIDATE["claim_a_text"], CANDIDATE["claim_b_text"])

    assert result["verdict"] == "CONTRADICTION"
    assert result["verified"] is True


@pytest.mark.asyncio
async def test_context_difference_is_not_a_contradiction():
    verifier = ContradictionVerifier(gateway=_ScriptedGateway([
        {
            "verdict": "CONTEXT_DIFFERENCE",
            "differing_condition": "adult vs. pediatric population",
            "reasoning": "Different populations studied.",
        },
    ]))

    result = await verifier.verify(CANDIDATE["claim_a_text"], CANDIDATE["claim_b_text"])

    assert result["verdict"] == "CONTEXT_DIFFERENCE"
    assert result["differing_condition"] == "adult vs. pediatric population"


@pytest.mark.asyncio
async def test_verify_batch_splits_candidates_by_verdict():
    verifier = ContradictionVerifier(gateway=_ScriptedGateway([
        {"verdict": "CONTRADICTION", "differing_condition": None, "reasoning": "..."},
        {"verdict": "CONTEXT_DIFFERENCE", "differing_condition": "dosage", "reasoning": "..."},
        {"verdict": "NOT_RELATED", "differing_condition": None, "reasoning": "..."},
    ]))

    result = await verifier.verify_batch([CANDIDATE, CANDIDATE, CANDIDATE])

    assert result["stats"] == {
        "candidates": 3,
        "confirmed_contradictions": 1,
        "context_differences": 1,
        "not_related": 1,
    }
    assert len(result["contradictions"]) == 1
    assert len(result["context_differences"]) == 1
    assert len(result["not_related"]) == 1


@pytest.mark.asyncio
async def test_verifier_failure_fails_closed_not_as_contradiction():
    """A flaky LLM call must not silently inflate the contradiction count."""
    verifier = ContradictionVerifier(gateway=_BrokenGateway())

    result = await verifier.verify(CANDIDATE["claim_a_text"], CANDIDATE["claim_b_text"])

    assert result["verdict"] == "CONTEXT_DIFFERENCE"
    assert result["verified"] is False


@pytest.mark.asyncio
async def test_invalid_verdict_string_falls_back_to_context_difference():
    verifier = ContradictionVerifier(gateway=_ScriptedGateway([
        {"verdict": "MAYBE", "differing_condition": None, "reasoning": "unsure"},
    ]))

    result = await verifier.verify(CANDIDATE["claim_a_text"], CANDIDATE["claim_b_text"])

    assert result["verdict"] == "CONTEXT_DIFFERENCE"
