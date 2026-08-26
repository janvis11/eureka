"""Hypothesis generation from evidence."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.services.model_gateway import (
    ChatMessage,
    GenerationRequest,
    create_gateway,
)
from app.services.discovery.heuristic_priors import score_hypothesis

logger = logging.getLogger(__name__)


HYPOTHESIS_GENERATION_PROMPT = """Based on the evidence provided, generate novel research hypotheses.

Evidence Summary:
{evidence_summary}

Key Entities: {entities}
Known Gaps: {gaps}
Contradictions: {contradictions}

For each hypothesis, provide:
- hypothesis: Clear, testable statement
- why_it_matters: Why this is important
- supporting_evidence: Brief summary of supporting evidence
- counter_evidence: Any opposing evidence
- novelty_score: 0.0-1.0 (how new is this?)
- impact_score: 0.0-1.0 (potential impact)
- feasibility_score: 0.0-1.0 (how testable is this?)
- falsifiability_score: 0.0-1.0 (can it be proven false?)

Generate 3-7 hypotheses. Respond ONLY with a JSON array:
[
  {{
    "hypothesis": "...",
    "why_it_matters": "...",
    "supporting_evidence": ["..."],
    "counter_evidence": ["..."],
    "novelty_score": 0.7,
    "impact_score": 0.8,
    "feasibility_score": 0.6,
    "falsifiability_score": 0.9
  }}
]
"""


class HypothesisGenerator:
    """Generates research hypotheses from evidence."""

    def __init__(self, gateway=None):
        """Initialize hypothesis generator."""
        self._gateway = gateway or create_gateway()

    async def generate(
        self,
        evidence_items: List[Dict[str, Any]],
        entities: Optional[List[str]] = None,
        gaps: Optional[List[Dict[str, Any]]] = None,
        contradictions: Optional[List[Dict[str, Any]]] = None,
        max_hypotheses: int = 5,
    ) -> List[Dict[str, Any]]:
        """Generate hypotheses from evidence.

        Args:
            evidence_items: List of evidence items
            entities: Optional list of key entities
            gaps: Optional list of known gaps
            contradictions: Optional list of contradictions
            max_hypotheses: Maximum hypotheses to generate

        Returns:
            List of generated hypotheses
        """
        if not evidence_items:
            return []

        # Build evidence summary
        evidence_summary = self._build_evidence_summary(evidence_items)
        entity_str = ", ".join(entities[:5]) if entities else "auto-detect"
        gap_str = ", ".join([g.get("description", "")[:50] for g in (gaps or [])[:3]]) or "none identified"
        contradiction_str = ", ".join([c.get("entity", "") for c in (contradictions or [])[:3]]) or "none identified"

        try:
            result = await self._gateway.generate(
                GenerationRequest(
                    messages=[
                        ChatMessage(
                            role="system",
                            content="Generate novel, testable research hypotheses. Return ONLY valid JSON.",
                        ),
                        ChatMessage(
                            role="user",
                            content=HYPOTHESIS_GENERATION_PROMPT.format(
                                evidence_summary=evidence_summary,
                                entities=entity_str,
                                gaps=gap_str,
                                contradictions=contradiction_str,
                            ),
                        ),
                    ],
                    temperature=0.4,  # Higher temperature for creativity
                    max_tokens=1500,
                    json_mode=True,
                )
            )

            hypotheses = self._parse_hypotheses(result.text)

            # Score each hypothesis
            for hyp in hypotheses:
                scores = score_hypothesis(
                    hyp.get("hypothesis", ""),
                    [{"text": e} for e in hyp.get("supporting_evidence", [])],
                    [{"text": e} for e in hyp.get("counter_evidence", [])],
                )
                hyp["scores"] = scores.to_dict()

            # Sort by overall score and limit
            hypotheses.sort(key=lambda x: x.get("scores", {}).get("overall", 0), reverse=True)
            return hypotheses[:max_hypotheses]

        except Exception as e:
            logger.error(f"Hypothesis generation failed: {e}")
            return []

    def _build_evidence_summary(self, evidence_items: List[Dict[str, Any]]) -> str:
        """Build a summary of evidence for the prompt."""
        lines = []

        for i, item in enumerate(evidence_items[:10], 1):
            text = item.get("text", "")[:200]
            score = item.get("score", 0)
            lines.append(f"[{i}] (score={score:.2f}) {text}")

        return "\n".join(lines)

    def _parse_hypotheses(self, text: str) -> List[Dict[str, Any]]:
        """Parse LLM output into hypotheses."""
        import json
        import re

        match = re.search(r"\[.*?\]", text, re.DOTALL)
        if not match:
            return []

        try:
            hypotheses = json.loads(match.group())
            if not isinstance(hypotheses, list):
                return []

            parsed = []
            for hyp in hypotheses:
                if not isinstance(hyp, dict):
                    continue

                parsed.append({
                    "hypothesis": hyp.get("hypothesis", ""),
                    "why_it_matters": hyp.get("why_it_matters", ""),
                    "supporting_evidence": hyp.get("supporting_evidence", []) or [],
                    "counter_evidence": hyp.get("counter_evidence", []) or [],
                    "novelty_score": float(hyp.get("novelty_score", 0.5)),
                    "impact_score": float(hyp.get("impact_score", 0.5)),
                    "feasibility_score": float(hyp.get("feasibility_score", 0.5)),
                    "falsifiability_score": float(hyp.get("falsifiability_score", 0.5)),
                })

            return parsed

        except (json.JSONDecodeError, ValueError):
            return []
