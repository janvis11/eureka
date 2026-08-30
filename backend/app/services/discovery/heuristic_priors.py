"""Heuristic priors for ranking hypotheses — NOT validated scores.

Renamed from `scoring.py`. Only
`evidence_strength` is grounded in real signal: actual retrieval scores and
counter-evidence counts. `novelty`, `impact`, `feasibility`, and
`falsifiability` are keyword/substring matches against the hypothesis text
the LLM itself wrote — an LLM that happens to say "dramatically" scores
higher on impact regardless of whether the hypothesis is any good. That is
a cheap prior for sorting a list, not a validated measurement, and callers
must not present it to users as one.

Every score this module returns carries a `basis` tag of either
"heuristic_keyword_match" or "retrieval_grounded" so API responses and the
UI can label it honestly instead of presenting a rubric-shaped number as
fact.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Dimensions that are real signal vs. keyword-matching priors.
_GROUNDED_DIMENSIONS = {"evidence_strength"}
_HEURISTIC_DIMENSIONS = {"novelty", "impact", "feasibility", "falsifiability"}


@dataclass
class HypothesisScore:
    """Score breakdown for a hypothesis.

    `overall` is a weighted blend of one grounded signal and four keyword
    heuristics — treat it as a sort key, not a confidence measure.
    """
    novelty: float = 0.0
    evidence_strength: float = 0.0
    impact: float = 0.0
    feasibility: float = 0.0
    falsifiability: float = 0.0
    overall: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        basis = {
            dim: ("retrieval_grounded" if dim in _GROUNDED_DIMENSIONS else "heuristic_keyword_match")
            for dim in ("novelty", "evidence_strength", "impact", "feasibility", "falsifiability")
        }
        return {
            "novelty": self.novelty,
            "evidence_strength": self.evidence_strength,
            "impact": self.impact,
            "feasibility": self.feasibility,
            "falsifiability": self.falsifiability,
            "overall": self.overall,
            "basis": basis,
            "disclaimer": (
                "novelty/impact/feasibility/falsifiability are heuristic priors "
                "from keyword matching on LLM-generated text, not validated "
                "scores. Only evidence_strength is grounded in retrieval data."
            ),
        }


def score_hypothesis(
    hypothesis_text: str,
    supporting_evidence: List[Dict[str, Any]],
    counter_evidence: List[Dict[str, Any]],
    graph_path_length: Optional[int] = None,
    novelty_keywords: Optional[List[str]] = None,
) -> HypothesisScore:
    """Score a hypothesis based on multiple criteria.

    Weighting (a sort key, not a validated rubric):
    - novelty (0.25): heuristic keyword match + graph path length
    - evidence_strength (0.25): grounded in real retrieval scores
    - impact (0.20): heuristic keyword match
    - feasibility (0.15): heuristic keyword match
    - falsifiability (0.15): heuristic keyword match

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
    """Heuristic keyword match, boosted by real graph path length when available."""
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
    """The one grounded dimension: derived from actual retrieval scores and
    counter-evidence counts, not text pattern matching."""
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
    """Heuristic keyword match — an LLM that writes "dramatically" scores
    higher here regardless of whether the hypothesis matters."""
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
    """Heuristic keyword match for concrete, testable-sounding language."""
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
    """Heuristic keyword match for conditional/predictive language."""
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
    """Rank hypotheses by overall heuristic-prior score (a sort key, not a
    validated measurement — see module docstring)."""
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
