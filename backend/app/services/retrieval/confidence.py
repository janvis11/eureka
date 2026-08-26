"""Retrieval confidence + abstention gate.

A system that says "I found 3 chunks, all below 0.42 similarity, from one
paper — I'm not confident enough to answer this" demonstrates more
judgment than a large agent pipeline. This module computes that confidence
from retrieval signals *before* the LLM is asked to answer, so a weak
retrieval never gets to produce a fluent-sounding answer anyway.

Confidence blends three signals actually available to the vector/RAG path:
- top1_similarity: how good the single best match is (a swarm of weak
  matches shouldn't outscore one strong one)
- avg_similarity: overall relevance of the retrieved set
- source_diversity: how many distinct documents corroborate the answer
  (one paper repeated N times is weaker evidence than N different papers)

This is not the full confidence formula that's possible here (rerank
agreement and graph corroboration are natural next signals) — those
aren't wired into this code path yet. See docs/LIMITATIONS.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


DEFAULT_ABSTENTION_THRESHOLD = 0.35


@dataclass
class ConfidenceResult:
    score: float
    should_answer: bool
    signals: Dict[str, float] = field(default_factory=dict)
    reason: Optional[str] = None
    what_would_help: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 3),
            "should_answer": self.should_answer,
            "signals": {k: round(v, 3) for k, v in self.signals.items()},
            "reason": self.reason,
            "what_would_help": self.what_would_help,
        }


def _l2_distance_to_similarity(distance: float) -> float:
    """Normalize a FAISS L2 distance (unbounded, smaller = closer) into a
    rough 0..1 similarity. This is a heuristic normalization, not a
    calibrated probability — see docs/LIMITATIONS.md."""
    return max(0.0, 1.0 - distance / 100.0)


def compute_confidence(
    context: List[Dict[str, Any]],
    threshold: float = DEFAULT_ABSTENTION_THRESHOLD,
) -> ConfidenceResult:
    """Compute retrieval confidence and decide whether to answer or abstain.

    Args:
        context: Retrieved chunks, each with an optional 'distance' (FAISS
            L2, smaller is better) and 'metadata.document_id'.
        threshold: Minimum confidence required to answer.

    Returns:
        ConfidenceResult with should_answer=False when evidence is too weak.
    """
    if not context:
        return ConfidenceResult(
            score=0.0,
            should_answer=False,
            signals={"evidence_count": 0},
            reason="no_evidence_retrieved",
            what_would_help="Upload documents covering this topic, or rephrase the question.",
        )

    similarities = [
        _l2_distance_to_similarity(c.get("distance", 100.0)) for c in context
    ]
    top1_similarity = max(similarities)
    avg_similarity = sum(similarities) / len(similarities)

    distinct_docs = {
        c.get("metadata", {}).get("document_id")
        for c in context
        if c.get("metadata", {}).get("document_id") is not None
    }
    source_diversity = min(1.0, len(distinct_docs) / 2) if distinct_docs else 0.0

    score = (
        0.5 * top1_similarity
        + 0.3 * avg_similarity
        + 0.2 * source_diversity
    )
    score = max(0.0, min(1.0, score))

    signals = {
        "top1_similarity": top1_similarity,
        "avg_similarity": avg_similarity,
        "source_diversity": source_diversity,
        "evidence_count": float(len(context)),
        "distinct_sources": float(len(distinct_docs)),
    }

    if score < threshold:
        return ConfidenceResult(
            score=score,
            should_answer=False,
            signals=signals,
            reason="insufficient_evidence",
            what_would_help=(
                f"Found {len(context)} chunk(s) from {len(distinct_docs) or 1} "
                f"source(s), best match at {top1_similarity:.2f} similarity — "
                "below the confidence threshold. Try a more specific question "
                "or upload documents that directly cover this topic."
            ),
        )

    return ConfidenceResult(score=score, should_answer=True, signals=signals)
