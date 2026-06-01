"""Fake / test provider for the model gateway.

Returns deterministic results — no API calls, no model downloads.
Use this in tests and for offline development.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import List

from app.services.model_gateway.base import (
    EmbeddingRequest,
    EmbeddingResult,
    GenerationRequest,
    GenerationResult,
    RerankResult,
)

logger = logging.getLogger(__name__)

# Embedding dimension used by the fake provider
FAKE_EMBEDDING_DIM = 384


class FakeProvider:
    """Deterministic provider for testing — no external dependencies."""

    def __init__(self, embedding_dim: int = FAKE_EMBEDDING_DIM):
        self._embedding_dim = embedding_dim
        logger.info("FakeProvider initialized (test mode)")

    # -----------------------------------------------------------------------
    # Generation
    # -----------------------------------------------------------------------
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Return a canned JSON response based on the prompt."""
        prompt_text = " ".join(m.content for m in request.messages).lower()

        # Return structured JSON when the prompt seems to expect it. More
        # specific tasks must be checked before generic "research" prompts.
        if "hypothesis" in prompt_text:
            hypothesis_payload = {
                "hypothesis": "Test hypothesis statement.",
                "rationale": "Test rationale.",
                "evidence": ["Test supporting evidence."],
                "counter_evidence": ["Test counter-evidence gap."],
                "methodology": "Test methodology.",
                "validation_plan": "Test validation plan.",
                "expected_impact": "Test impact.",
                "novelty": "Test novelty.",
                "feasibility": "Test feasibility.",
                "falsifiability": "A negative test result would disprove it.",
                "novelty_score": 0.7,
                "feasibility_score": 0.8,
                "falsifiability_score": 0.9,
                "confidence": 0.75,
                "evidence_sources": ["method", "outcome"],
            }
            text = json.dumps([hypothesis_payload] if "json array" in prompt_text else hypothesis_payload)
        elif "trend" in prompt_text:
            text = json.dumps({
                "trends": [
                    {
                        "title": "Fake trend",
                        "description": "Rising interest.",
                        "velocity": "Rising",
                        "trend_score": 0.8,
                    }
                ]
            })
        elif "contradict" in prompt_text:
            text = json.dumps({
                "has_contradiction": True,
                "title": "Test contradiction",
                "description": "Two claims conflict.",
                "confidence": 0.7,
                "impact": "medium",
            })
        elif "rank" in prompt_text:
            text = json.dumps({
                "ranked_gaps": [
                    {
                        "title": "Fake gap for testing",
                        "rank": 1,
                        "novelty_score": 0.9,
                        "impact_score": 0.8,
                        "feasibility_score": 0.7,
                        "final_score": 0.8,
                        "reasoning": "Test reasoning.",
                    }
                ]
            })
        elif "summar" in prompt_text:
            text = json.dumps({
                "title": "Test Summary",
                "core_problem": "Test problem.",
                "method": "Test method.",
                "key_results": ["Result 1", "Result 2"],
                "limitations": ["Limitation 1"],
                "future_work": ["Future work 1"],
            })
        elif "valid" in prompt_text:
            text = json.dumps({
                "valid": True,
                "testability_score": 0.8,
                "novelty_score": 0.7,
                "evidence_support_score": 0.9,
                "feasibility_score": 0.8,
                "issues": [],
                "suggested_fix": "",
                "overall_score": 0.8,
            })
        elif "experiment" in prompt_text:
            text = json.dumps({
                "experiments": [
                    {
                        "experiment_title": "Test experiment",
                        "goal": "Validate hypothesis.",
                        "methodology": "RCT.",
                        "data_required": "Dataset X.",
                        "metrics": "Accuracy.",
                        "expected_outcome": "Positive result.",
                    }
                ]
            })
        elif "report" in prompt_text:
            text = "# Test Report\n\nThis is a fake discovery report for testing."
        elif "keyphrase" in prompt_text or "keyword" in prompt_text:
            text = "machine learning, neural networks, deep learning"
        elif "claim" in prompt_text:
            text = json.dumps([
                {
                    "text": "The method improves the measured outcome.",
                    "claim_type": "finding",
                    "entities": ["method", "outcome"],
                    "polarity": "positive",
                    "confidence": 0.7,
                    "source_quote": "The method improves the measured outcome.",
                }
            ])
        elif "relationship" in prompt_text:
            text = json.dumps([
                {
                    "subject": "method",
                    "predicate": "improves",
                    "object": "outcome",
                    "evidence": "The method improves the measured outcome.",
                    "confidence": 0.7,
                }
            ])
        elif "gap" in prompt_text or "research" in prompt_text:
            text = json.dumps({
                "gaps": [
                    {
                        "title": "Fake gap for testing",
                        "description": "This is a test gap.",
                        "type": "methodological",
                        "impact": "high",
                        "confidence": 0.85,
                    }
                ]
            })
        else:
            text = "This is a test response from the fake provider."

        return GenerationResult(
            text=text,
            model="fake-model",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        )

    # -----------------------------------------------------------------------
    # Embeddings  (deterministic hash-based)
    # -----------------------------------------------------------------------
    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        """Generate deterministic embeddings from text hashes."""
        embeddings = []
        for text in request.texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            # Expand the 32-byte hash to fill the embedding dimension
            values = []
            for i in range(self._embedding_dim):
                byte_val = digest[i % len(digest)]
                # Normalize to [-1, 1]
                values.append((byte_val / 127.5) - 1.0)
            embeddings.append(values)

        return EmbeddingResult(
            embeddings=embeddings,
            model="fake-embedding",
            dimension=self._embedding_dim,
        )

    # -----------------------------------------------------------------------
    # Reranking
    # -----------------------------------------------------------------------
    async def rerank(
        self, query: str, documents: List[str], top_k: int = 10
    ) -> List[RerankResult]:
        """Return documents in original order with decaying scores."""
        return [
            RerankResult(index=i, score=1.0 / (i + 1), text=doc)
            for i, doc in enumerate(documents[:top_k])
        ]
