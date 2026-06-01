"""Scoring utilities for hypotheses and discoveries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class HypothesisScore:
    """Score breakdown for a hypothesis."""
    novelty: float = 0.0
    evidence_strength: float = 0.0
    impact: float = 0.0
    feasibility: float = 0.0
    falsifiability: float = 0.0
    overall: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "novelty": self.novelty,
            "evidence_strength": self.evidence_strength,
            "impact": self.impact,
            "feasibility": self.feasibility,
            "falsifiability": self.falsifiability,
            "overall": self.overall,
        }


def score_hypothesis(
    hypothesis_text: str,
    supporting_evidence: List[Dict[str, Any]],
    counter_evidence: List[Dict[str, Any]],
    graph_path_length: Optional[int] = None,
    novelty_keywords: Optional[List[str]] = None,
) -> HypothesisScore:
    """Score a hypothesis based on multiple criteria.

    Scoring rubric:
    - novelty (0.25): How new/unexpected is this?
    - evidence_strength (0.25): How strong is the supporting evidence?
    - impact (0.20): What's the potential impact?
    - feasibility (0.15): How feasible is validation?
    - falsifiability (0.15): Is it testable/falsifiable?

    Args:
        hypothesis_text: The hypothesis text
        supporting_evidence: List of supporting evidence items
        counter_evidence: List of counter evidence items
        graph_path_length: Length of graph path if applicable
        novelty_keywords: Optional keywords indicating novelty

    Returns:
        HypothesisScore with breakdown
    """
    # Novelty score
    novelty = _calculate_novelty(hypothesis_text, novelty_keywords, graph_path_length)

    # Evidence strength
    evidence_strength = _calculate_evidence_strength(supporting_evidence, counter_evidence)

    # Impact score
    impact = _calculate_impact(hypothesis_text)

    # Feasibility score
    feasibility = _calculate_feasibility(hypothesis_text)

    # Falsifiability score
    falsifiability = _calculate_falsifiability(hypothesis_text)

    # Overall weighted score
    overall = (
        0.25 * novelty +
        0.25 * evidence_strength +
        0.20 * impact +
        0.15 * feasibility +
        0.15 * falsifiability
    )

    return HypothesisScore(
        novelty=novelty,
        evidence_strength=evidence_strength,
        impact=impact,
        feasibility=feasibility,
        falsifiability=falsifiability,
        overall=overall,
    )


def _calculate_novelty(
    text: str,
    keywords: Optional[List[str]] = None,
    path_length: Optional[int] = None,
) -> float:
    """Calculate novelty score."""
    score = 0.5  # Base score

    # Novelty keywords boost
    novelty_terms = [
        "first", "novel", "new", "previously unknown", "unprecedented",
        "discover", "propose", "introduce", "bridge", "connect",
    ]
    if keywords:
        novelty_terms.extend(keywords)

    text_lower = text.lower()
    for term in novelty_terms:
        if term in text_lower:
            score += 0.1
            break

    # Long graph paths suggest novel connections
    if path_length and path_length >= 3:
        score += 0.2

    return min(1.0, score)


def _calculate_evidence_strength(
    supporting: List[Dict[str, Any]],
    counter: List[Dict[str, Any]],
) -> float:
    """Calculate evidence strength score."""
    if not supporting:
        return 0.0

    # Average confidence of supporting evidence
    avg_support = sum(e.get("score", 0.5) for e in supporting) / len(supporting)

    # Penalty for counter-evidence
    counter_penalty = 0.0
    if counter:
        avg_counter = sum(e.get("score", 0.5) for e in counter) / len(counter)
        counter_penalty = 0.5 * min(1.0, len(counter) / 3) * avg_counter

    # Evidence count bonus
    count_bonus = min(0.2, len(supporting) * 0.05)

    score = avg_support * 0.7 + count_bonus - counter_penalty
    return max(0.0, min(1.0, score))


def _calculate_impact(text: str) -> float:
    """Calculate potential impact score."""
    impact_terms = [
        "significantly", "substantially", "dramatically",
        "improve", "enhance", "transform", "enable",
        "breakthrough", "paradigm", "fundamental",
        "wide-ranging", "broad", "general",
    ]

    text_lower = text.lower()
    matches = sum(1 for term in impact_terms if term in text_lower)

    # Base score + bonus for impact language
    score = 0.5 + min(0.5, matches * 0.1)
    return min(1.0, score)


def _calculate_feasibility(text: str) -> float:
    """Calculate feasibility score."""
    # Look for concrete, testable elements
    feasibility_terms = [
        "experiment", "test", "measure", "evaluate",
        "dataset", "benchmark", "corpus",
        "method", "approach", "technique",
        "validate", "verify", "confirm",
    ]

    text_lower = text.lower()
    matches = sum(1 for term in feasibility_terms if term in text_lower)

    # More specific = more feasible
    score = 0.3 + min(0.7, matches * 0.15)
    return min(1.0, score)


def _calculate_falsifiability(text: str) -> float:
    """Calculate falsifiability score."""
    # Falsifiable hypotheses have clear predictions
    falsifiability_terms = [
        "will", "would", "should", "expect",
        "increase", "decrease", "reduce", "improve",
        "correlation", "cause", "effect",
        "if", "then", "when",
    ]

    text_lower = text.lower()
    matches = sum(1 for term in falsifiability_terms if term in text_lower)

    # Conditional statements suggest testability
    if "if" in text_lower and "then" in text_lower:
        matches += 2

    score = 0.3 + min(0.7, matches * 0.1)
    return min(1.0, score)


def rank_hypotheses(
    hypotheses: List[Dict[str, Any]],
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """Rank hypotheses by overall score."""
    scored = []
    for hyp in hypotheses:
        score = score_hypothesis(
            hyp.get("text", ""),
            hyp.get("supporting_evidence", []),
            hyp.get("counter_evidence", []),
        )
        hyp["scores"] = score.to_dict()
        scored.append(hyp)

    scored.sort(key=lambda x: x["scores"]["overall"], reverse=True)
    return scored[:top_k]
