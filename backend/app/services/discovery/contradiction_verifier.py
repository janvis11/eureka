"""LLM verification stage for candidate contradictions.

`ContradictionMiner` is a cheap, high-recall candidate generator: it flags
any two claims about the same entity with opposite-polarity keywords
(improves/reduces, increases/decreases, ...). That fires on genuine
contradictions but just as often on claims that differ by population,
dataset, dosage, or time period — those are context differences, not
contradictions, and conflating them is a real credibility risk in the
discovery pipeline.

This module is the second stage: an LLM judges each candidate pair with a
strict 3-way verdict (CONTRADICTION / CONTEXT_DIFFERENCE / NOT_RELATED) and
must name the differing condition when it picks CONTEXT_DIFFERENCE. The
miner stays a regex/keyword pass because it's cheap and high-recall; the
LLM only verifies, because that's where judgment is actually needed —
don't put an LLM where a keyword list works, don't put a keyword list where
judgment is needed.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.services.model_gateway import (
    ChatMessage,
    GenerationRequest,
    create_gateway,
)

logger = logging.getLogger(__name__)


VERIFICATION_PROMPT = """Two claims were flagged as a possible contradiction because they \
mention the same entity with opposite polarity language. Decide whether they \
actually contradict each other.

Claim A: {claim_a}
Claim B: {claim_b}

Classify the relationship as exactly one of:
- CONTRADICTION: the claims make incompatible assertions about the same \
entity under the same conditions.
- CONTEXT_DIFFERENCE: the claims differ because of a different population, \
dataset, dosage, timeframe, metric, or other condition — not a genuine \
disagreement. You MUST name the differing condition.
- NOT_RELATED: the claims are not actually about the same thing, despite \
sharing an entity.

Default to CONTEXT_DIFFERENCE or NOT_RELATED when uncertain — only pick \
CONTRADICTION when the claims genuinely cannot both be true under the same \
conditions.

Respond ONLY with JSON:
{{
  "verdict": "CONTRADICTION|CONTEXT_DIFFERENCE|NOT_RELATED",
  "differing_condition": "required if CONTEXT_DIFFERENCE, else null",
  "reasoning": "one sentence"
}}
"""

_VALID_VERDICTS = {"CONTRADICTION", "CONTEXT_DIFFERENCE", "NOT_RELATED"}


class ContradictionVerifier:
    """Second-stage LLM filter over candidate contradiction pairs."""

    def __init__(self, gateway=None):
        self._gateway = gateway or create_gateway()

    async def verify(self, claim_a: str, claim_b: str) -> Dict[str, Any]:
        """Classify one candidate pair. Fails closed to CONTEXT_DIFFERENCE
        (not CONTRADICTION) on any parse or provider error, so a flaky LLM
        call can't inflate the contradiction count."""
        try:
            result = await self._gateway.generate(
                GenerationRequest(
                    messages=[
                        ChatMessage(
                            role="system",
                            content=(
                                "You verify candidate contradictions between "
                                "scientific claims. Be conservative — most "
                                "same-entity, opposite-polarity claim pairs "
                                "differ by context, not by genuine "
                                "disagreement. Return ONLY valid JSON."
                            ),
                        ),
                        ChatMessage(
                            role="user",
                            content=VERIFICATION_PROMPT.format(
                                claim_a=claim_a, claim_b=claim_b
                            ),
                        ),
                    ],
                    temperature=0.0,
                    max_tokens=300,
                    json_mode=True,
                )
            )
            return self._parse(result.text)
        except Exception as e:
            logger.warning(f"Contradiction verification failed, treating as unverified: {e}")
            return {
                "verdict": "CONTEXT_DIFFERENCE",
                "differing_condition": "unknown (verification call failed)",
                "reasoning": f"Verifier error: {e}",
                "verified": False,
            }

    def _parse(self, text: str) -> Dict[str, Any]:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return {
                "verdict": "CONTEXT_DIFFERENCE",
                "differing_condition": "unknown (could not parse verifier output)",
                "reasoning": "Unparseable verifier response",
                "verified": False,
            }
        try:
            data = json.loads(match.group())
            verdict = str(data.get("verdict", "")).strip().upper()
            if verdict not in _VALID_VERDICTS:
                verdict = "CONTEXT_DIFFERENCE"
            return {
                "verdict": verdict,
                "differing_condition": data.get("differing_condition"),
                "reasoning": data.get("reasoning", ""),
                "verified": True,
            }
        except json.JSONDecodeError:
            return {
                "verdict": "CONTEXT_DIFFERENCE",
                "differing_condition": "unknown (invalid JSON from verifier)",
                "reasoning": "Invalid JSON from verifier",
                "verified": False,
            }

    async def verify_batch(
        self,
        candidates: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Verify every candidate pair from ContradictionMiner.

        Returns a dict with the confirmed contradictions plus the honest
        breakdown of what happened to the rest — this is what makes
        precision/recall measurable instead of asserted.
        """
        confirmed: List[Dict[str, Any]] = []
        context_differences: List[Dict[str, Any]] = []
        not_related: List[Dict[str, Any]] = []

        for candidate in candidates:
            verdict = await self.verify(
                candidate.get("claim_a_text", ""),
                candidate.get("claim_b_text", ""),
            )
            candidate = {**candidate, "verification": verdict}

            if verdict["verdict"] == "CONTRADICTION":
                confirmed.append(candidate)
            elif verdict["verdict"] == "CONTEXT_DIFFERENCE":
                context_differences.append(candidate)
            else:
                not_related.append(candidate)

        return {
            "contradictions": confirmed,
            "context_differences": context_differences,
            "not_related": not_related,
            "stats": {
                "candidates": len(candidates),
                "confirmed_contradictions": len(confirmed),
                "context_differences": len(context_differences),
                "not_related": len(not_related),
            },
        }
