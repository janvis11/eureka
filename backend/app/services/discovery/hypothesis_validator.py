"""Hypothesis validation."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.services.model_gateway import (
    ChatMessage,
    GenerationRequest,
    create_gateway,
)

logger = logging.getLogger(__name__)


VALIDATION_PROMPT = """Validate the following hypothesis against the evidence.

Hypothesis: {hypothesis}

Supporting Evidence:
{supporting_evidence}

Counter Evidence:
{counter_evidence}

Answer the following questions:
1. Does the evidence actually support the hypothesis? (yes/no/partially)
2. Is there significant counter-evidence? (yes/no/some)
3. Is this hypothesis already well-established? (yes/no/unclear)
4. Is it clearly testable? (yes/no/partially)
5. What experiment would falsify it?

Respond ONLY with JSON:
{{
  "evidence_supports": "yes|no|partially",
  "has_counter_evidence": "yes|no|some",
  "is_novel": "yes|no|unclear",
  "is_testable": "yes|no|partially",
  "falsification_experiment": "...",
  "validation_notes": "...",
  "confidence": 0.0
}}
"""


class HypothesisValidator:
    """Validates hypotheses against evidence."""

    def __init__(self, gateway=None):
        """Initialize hypothesis validator."""
        self._gateway = gateway or create_gateway()

    async def validate(
        self,
        hypothesis: str,
        supporting_evidence: List[str],
        counter_evidence: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Validate a hypothesis.

        Args:
            hypothesis: Hypothesis text
            supporting_evidence: List of supporting evidence texts
            counter_evidence: Optional list of counter evidence texts

        Returns:
            Validation result with scores and notes
        """
        supporting_text = "\n".join(f"- {e}" for e in supporting_evidence[:5])
        counter_text = "\n".join(f"- {e}" for e in (counter_evidence or [])[:3])

        try:
            result = await self._gateway.generate(
                GenerationRequest(
                    messages=[
                        ChatMessage(
                            role="system",
                            content="Validate hypotheses critically. Return ONLY valid JSON.",
                        ),
                        ChatMessage(
                            role="user",
                            content=VALIDATION_PROMPT.format(
                                hypothesis=hypothesis,
                                supporting_evidence=supporting_text or "None provided",
                                counter_evidence=counter_text or "None provided",
                            ),
                        ),
                    ],
                    temperature=0.1,
                    max_tokens=500,
                    json_mode=True,
                )
            )

            validation = self._parse_validation(result.text)
            return validation

        except Exception as e:
            logger.error(f"Hypothesis validation failed: {e}")
            return {
                "evidence_supports": "unclear",
                "has_counter_evidence": "unclear",
                "is_novel": "unclear",
                "is_testable": "unclear",
                "confidence": 0.0,
                "error": str(e),
            }

    def _parse_validation(self, text: str) -> Dict[str, Any]:
        """Parse LLM output into validation result."""
        import json
        import re

        match = re.search(r"\{.*?\}", text, re.DOTALL)
        if not match:
            return {"error": "Could not parse validation result"}

        try:
            data = json.loads(match.group())

            return {
                "evidence_supports": self._map_to_bool(data.get("evidence_supports", "unclear")),
                "has_counter_evidence": data.get("has_counter_evidence", "unclear"),
                "is_novel": data.get("is_novel", "unclear"),
                "is_testable": self._map_to_bool(data.get("is_testable", "unclear")),
                "falsification_experiment": data.get("falsification_experiment", ""),
                "validation_notes": data.get("validation_notes", ""),
                "confidence": float(data.get("confidence", 0.5)),
            }

        except (json.JSONDecodeError, ValueError):
            return {"error": "Invalid validation format"}

    def _map_to_bool(self, value: str) -> bool:
        """Map yes/no/partially to boolean."""
        if isinstance(value, bool):
            return value
        value = str(value).lower()
        if value in {"yes", "true"}:
            return True
        if value in {"partially", "some"}:
            return True  # Treat partial as weak yes
        return False

    def batch_validate(
        self,
        hypotheses: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Validate multiple hypotheses.

        Args:
            hypotheses: List of hypothesis dicts

        Returns:
            List of validation results
        """
        validations = []
        for hyp in hypotheses:
            result = self.validate(
                hyp.get("hypothesis", ""),
                hyp.get("supporting_evidence", []),
                hyp.get("counter_evidence", []),
            )
            validations.append(result)
        return validations
