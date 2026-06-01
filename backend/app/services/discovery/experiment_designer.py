"""Experiment design for hypothesis validation."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.services.model_gateway import (
    ChatMessage,
    GenerationRequest,
    create_gateway,
)

logger = logging.getLogger(__name__)


EXPERIMENT_DESIGN_PROMPT = """Design an experiment to validate or falsify the following hypothesis.

Hypothesis: {hypothesis}

Context:
- Why it matters: {why_it_matters}
- Supporting evidence: {supporting_evidence}
- Known limitations: {limitations}

Design a practical experiment including:
- dataset_needed: What data is required
- method: Experimental approach
- controls: Control conditions
- metrics: How to measure success
- expected_result: What would support the hypothesis
- failure_modes: What could go wrong
- estimated_cost: Rough cost/time estimate
- ethical_concerns: Any ethical/safety issues

Respond ONLY with JSON:
{{
  "dataset_needed": "...",
  "method": "...",
  "controls": ["control1", "control2"],
  "metrics": ["metric1", "metric2"],
  "expected_result": "...",
  "failure_modes": ["failure1", "failure2"],
  "estimated_cost": "...",
  "estimated_time": "...",
  "ethical_concerns": "..."
}}
"""


class ExperimentDesigner:
    """Designs experiments to validate hypotheses."""

    def __init__(self, gateway=None):
        """Initialize experiment designer."""
        self._gateway = gateway or create_gateway()

    async def design(
        self,
        hypothesis: str,
        why_it_matters: str = "",
        supporting_evidence: Optional[List[str]] = None,
        limitations: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Design an experiment for a hypothesis.

        Args:
            hypothesis: Hypothesis to test
            why_it_matters: Motivation
            supporting_evidence: Optional supporting evidence
            limitations: Known limitations

        Returns:
            Experiment design
        """
        evidence_str = "\n".join(f"- {e}" for e in (supporting_evidence or [])[:3])
        limitations_str = "\n".join(f"- {l}" for l in (limitations or [])[:3])

        try:
            result = await self._gateway.generate(
                GenerationRequest(
                    messages=[
                        ChatMessage(
                            role="system",
                            content="Design practical, falsifiable experiments. Return ONLY valid JSON.",
                        ),
                        ChatMessage(
                            role="user",
                            content=EXPERIMENT_DESIGN_PROMPT.format(
                                hypothesis=hypothesis,
                                why_it_matters=why_it_matters[:200],
                                supporting_evidence=evidence_str or "None provided",
                                limitations=limitations_str or "None provided",
                            ),
                        ),
                    ],
                    temperature=0.2,
                    max_tokens=800,
                    json_mode=True,
                )
            )

            design = self._parse_design(result.text)
            return design

        except Exception as e:
            logger.error(f"Experiment design failed: {e}")
            return {
                "error": str(e),
                "method": "Expert review needed",
            }

    def _parse_design(self, text: str) -> Dict[str, Any]:
        """Parse LLM output into experiment design."""
        import json
        import re

        match = re.search(r"\{.*?\}", text, re.DOTALL)
        if not match:
            return {"error": "Could not parse experiment design"}

        try:
            data = json.loads(match.group())

            return {
                "dataset_needed": data.get("dataset_needed", ""),
                "method": data.get("method", ""),
                "controls": data.get("controls", []) or [],
                "metrics": data.get("metrics", []) or [],
                "expected_result": data.get("expected_result", ""),
                "failure_modes": data.get("failure_modes", []) or [],
                "estimated_cost": data.get("estimated_cost", "Unknown"),
                "estimated_time": data.get("estimated_time", "Unknown"),
                "ethical_concerns": data.get("ethical_concerns", "None identified"),
            }

        except (json.JSONDecodeError, ValueError):
            return {"error": "Invalid design format"}

    def design_batch(
        self,
        hypotheses: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Design experiments for multiple hypotheses.

        Args:
            hypotheses: List of hypothesis dicts

        Returns:
            List of experiment designs
        """
        designs = []
        for hyp in hypotheses:
            design = self.design(
                hypothesis=hyp.get("hypothesis", ""),
                why_it_matters=hyp.get("why_it_matters", ""),
                supporting_evidence=hyp.get("supporting_evidence", []),
            )
            design["hypothesis_id"] = hyp.get("id", hyp.get("hypothesis", "")[:50])
            designs.append(design)
        return designs
