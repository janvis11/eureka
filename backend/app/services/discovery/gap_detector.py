"""Gap detection in research."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.services.model_gateway import (
    ChatMessage,
    GenerationRequest,
    create_gateway,
)

logger = logging.getLogger(__name__)


GAP_DETECTION_PROMPT = """Analyze the text for research gaps and open questions.

Look for:
- Explicit limitations mentioned by authors
- Future work suggestions
- Underexplored areas
- Missing evaluations or benchmarks
- Contradictions that need resolution
- Concepts mentioned but not deeply explored

Text:
{text}

Respond ONLY with a JSON array of gaps:
[
  {{
    "description": "Clear description of the gap",
    "gap_type": "limitation|future_work|missing_evaluation|contradiction|underexplored",
    "entities": ["Entity1", "Entity2"],
    "importance": 0.8,
    "evidence_quote": "quote from text"
  }}
]
"""


class GapDetector:
    """Detects research gaps in text."""

    def __init__(self, gateway=None):
        """Initialize gap detector."""
        self._gateway = gateway or create_gateway()

    async def detect_gaps(self, text: str) -> List[Dict[str, Any]]:
        """Detect research gaps in text.

        Args:
            text: Text to analyze

        Returns:
            List of detected gaps
        """
        if len(text) < 100:
            return []

        try:
            result = await self._gateway.generate(
                GenerationRequest(
                    messages=[
                        ChatMessage(
                            role="system",
                            content="Identify research gaps. Return ONLY valid JSON.",
                        ),
                        ChatMessage(
                            role="user",
                            content=GAP_DETECTION_PROMPT.format(text=text[:4000]),
                        ),
                    ],
                    temperature=0.2,
                    max_tokens=1000,
                    json_mode=True,
                )
            )

            gaps = self._parse_gaps(result.text)
            return gaps

        except Exception as e:
            logger.error(f"Gap detection failed: {e}")
            return []

    def _parse_gaps(self, text: str) -> List[Dict[str, Any]]:
        """Parse LLM output into gaps."""
        import json
        import re

        match = re.search(r"\[.*?\]", text, re.DOTALL)
        if not match:
            return []

        try:
            gaps = json.loads(match.group())
            if not isinstance(gaps, list):
                return []

            parsed = []
            for gap in gaps:
                if not isinstance(gap, dict):
                    continue

                gap_type = gap.get("gap_type", "underexplored")
                if gap_type not in {"limitation", "future_work", "missing_evaluation", "contradiction", "underexplored"}:
                    gap_type = "underexplored"

                parsed.append({
                    "description": gap.get("description", ""),
                    "gap_type": gap_type,
                    "entities": gap.get("entities", []) or [],
                    "importance": float(gap.get("importance", 0.5)),
                    "evidence_quote": gap.get("evidence_quote", ""),
                })

            return parsed

        except (json.JSONDecodeError, ValueError):
            return []

    def aggregate_gaps(
        self,
        all_gaps: List[Dict[str, Any]],
        min_importance: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """Aggregate and deduplicate gaps.

        Args:
            all_gaps: List of all detected gaps
            min_importance: Minimum importance threshold

        Returns:
            Aggregated list of unique gaps
        """
        # Filter by importance
        filtered = [g for g in all_gaps if g.get("importance", 0) >= min_importance]

        # Group by similar description
        grouped: Dict[str, Dict] = {}
        for gap in filtered:
            desc = gap.get("description", "")[:50].lower()
            if desc not in grouped:
                grouped[desc] = gap
            else:
                # Keep the one with higher importance
                if gap.get("importance", 0) > grouped[desc].get("importance", 0):
                    grouped[desc] = gap

        # Sort by importance
        aggregated = list(grouped.values())
        aggregated.sort(key=lambda x: x.get("importance", 0), reverse=True)

        return aggregated

    def find_gaps_from_claims(
        self,
        claims: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Extract gaps from claims (limitations and future work).

        Args:
            claims: List of extracted claims

        Returns:
            List of gaps derived from claims
        """
        gaps = []

        for claim in claims:
            claim_type = claim.get("claim_type", "")

            if claim_type == "limitation":
                gaps.append({
                    "description": f"Limitation: {claim.get('text', '')}",
                    "gap_type": "limitation",
                    "entities": claim.get("entities", []),
                    "importance": claim.get("confidence", 0.5),
                    "evidence_quote": claim.get("source_quote", ""),
                })

            elif claim_type == "future_work":
                gaps.append({
                    "description": f"Future work: {claim.get('text', '')}",
                    "gap_type": "future_work",
                    "entities": claim.get("entities", []),
                    "importance": claim.get("confidence", 0.5) + 0.1,
                    "evidence_quote": claim.get("source_quote", ""),
                })

        return gaps
