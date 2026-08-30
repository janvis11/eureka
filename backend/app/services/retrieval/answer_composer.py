"""Answer composer for retrieval results."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.services.model_gateway import (
    ChatMessage,
    GenerationRequest,
    create_gateway,
)
from app.services.retrieval.evidence_pack import EvidencePack, format_evidence_for_prompt

logger = logging.getLogger(__name__)


ANSWER_PROMPT = """You are a research assistant. Answer the query based ONLY on the provided evidence.

Query: {query}

Evidence:
{evidence}

Instructions:
1. Provide a direct answer based on the evidence
2. Cite evidence using [1], [2], etc.
3. Indicate uncertainty when evidence is weak or conflicting
4. If evidence is insufficient, say "Insufficient evidence to answer"
5. Distinguish between facts, inferences, and speculation

Answer:"""


class AnswerComposer:
    """Composes answers from retrieval evidence."""

    def __init__(self, gateway=None):
        """Initialize answer composer.

        Args:
            gateway: Optional model gateway instance
        """
        self._gateway = gateway or create_gateway()

    async def compose(
        self,
        query: str,
        evidence_pack: EvidencePack,
        max_context_items: int = 10,
    ) -> Dict[str, Any]:
        """Compose an answer from evidence.

        Args:
            query: Original query
            evidence_pack: Evidence pack
            max_context_items: Maximum evidence items to include

        Returns:
            Answer with metadata
        """
        # Format evidence
        formatted = format_evidence_for_prompt(evidence_pack)
        prompt = ANSWER_PROMPT.format(
            query=query,
            evidence=formatted,
        )

        try:
            result = await self._gateway.generate(
                GenerationRequest(
                    messages=[
                        ChatMessage(
                            role="system",
                            content="You are a research assistant. Answer based on evidence only. Cite sources.",
                        ),
                        ChatMessage(role="user", content=prompt),
                    ],
                    temperature=0.2,
                    max_tokens=800,
                )
            )

            answer = result.text.strip()

            # Calculate confidence based on evidence quality
            confidence = self._calculate_confidence(evidence_pack)

            return {
                "answer": answer,
                "confidence": confidence,
                "evidence_count": len(evidence_pack.items),
                "counter_evidence_count": len(evidence_pack.counter_evidence),
                "has_graph_paths": len(evidence_pack.graph_paths) > 0,
                "uncertainty_flags": self._detect_uncertainty(answer),
            }

        except Exception as e:
            logger.error(f"Answer composition failed: {e}")
            return {
                "answer": "Unable to compose answer due to technical error.",
                "confidence": 0.0,
                "error": str(e),
            }

    def _calculate_confidence(self, evidence_pack: EvidencePack) -> float:
        """Calculate confidence score for the answer."""
        if not evidence_pack.items:
            return 0.0

        # Base confidence from evidence count
        count_score = min(1.0, len(evidence_pack.items) / 5)

        # Average evidence score
        avg_score = sum(i.score for i in evidence_pack.items) / len(evidence_pack.items)

        # Penalty for counter-evidence
        counter_penalty = 0.0
        if evidence_pack.counter_evidence:
            counter_penalty = 0.3 * min(1.0, len(evidence_pack.counter_evidence) / 3)

        # Graph path bonus
        graph_bonus = 0.1 if evidence_pack.graph_paths else 0.0

        confidence = count_score * 0.3 + avg_score * 0.5 + graph_bonus - counter_penalty
        return max(0.0, min(1.0, confidence))

    def _detect_uncertainty(self, answer: str) -> List[str]:
        """Detect uncertainty markers in the answer."""
        import re

        uncertainty_patterns = [
            (r"\bmay\b", "possibility"),
            (r"\bmight\b", "possibility"),
            (r"\bcould\b", "possibility"),
            (r"\bpossibly\b", "possibility"),
            (r"\blikely\b", "probability"),
            (r"\buncertain\b", "explicit_uncertainty"),
            (r"\binsufficient evidence\b", "evidence_gap"),
            (r"\bfurther research\b", "research_needed"),
            (r"\bmore data\b", "data_gap"),
        ]

        flags = []
        for pattern, flag in uncertainty_patterns:
            if re.search(pattern, answer, re.IGNORECASE):
                flags.append(flag)

        return flags


def compose_short_answer(
    query: str,
    top_evidence: List[Dict[str, Any]],
) -> str:
    """Compose a short answer without LLM for simple queries."""
    if not top_evidence:
        return "No relevant information found."

    # Extract key sentences from top evidence
    texts = [e.get("text", "") for e in top_evidence[:3]]

    if len(texts) == 1:
        return texts[0][:300]

    # Combine top 2-3 pieces of evidence
    combined = " ".join(t[:150] for t in texts)
    return combined[:400]
