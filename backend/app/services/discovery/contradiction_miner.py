"""Contradiction mining between claims."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ContradictionMiner:
    """Finds contradictory claims."""

    def __init__(self):
        """Initialize contradiction miner."""
        self._contradiction_pairs = [
            ("positive", "negative"),
            ("improves", "reduces"),
            ("increases", "decreases"),
            ("supports", "undermines"),
        ]

    def find_contradictions(
        self,
        claims: List[Dict[str, Any]],
        entity_filter: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Find contradictory claims.

        Args:
            claims: List of claims with entities, polarity, text
            entity_filter: Optional list of entities to focus on

        Returns:
            List of contradiction candidates
        """
        contradictions = []

        # Group claims by entity
        claims_by_entity: Dict[str, List[Dict]] = {}
        for claim in claims:
            entities = claim.get("entities", [])
            for entity in entities:
                if entity_filter and entity not in entity_filter:
                    continue
                if entity not in claims_by_entity:
                    claims_by_entity[entity] = []
                claims_by_entity[entity].append(claim)

        # Find contradictions within each entity group
        for entity, entity_claims in claims_by_entity.items():
            if len(entity_claims) < 2:
                continue

            for i, claim_a in enumerate(entity_claims):
                for claim_b in entity_claims[i + 1:]:
                    if self._is_contradiction(claim_a, claim_b):
                        contradictions.append({
                            "entity": entity,
                            "claim_a_id": claim_a.get("id", self._hash_claim(claim_a)),
                            "claim_a_text": claim_a.get("text", ""),
                            "claim_b_id": claim_b.get("id", self._hash_claim(claim_b)),
                            "claim_b_text": claim_b.get("text", ""),
                            "contradiction_type": self._get_contradiction_type(claim_a, claim_b),
                            "severity": self._calculate_severity(claim_a, claim_b),
                            "resolution_hint": self._generate_resolution_hint(claim_a, claim_b),
                        })

        # Sort by severity
        contradictions.sort(key=lambda x: x["severity"], reverse=True)
        return contradictions

    def _is_contradiction(
        self,
        claim_a: Dict[str, Any],
        claim_b: Dict[str, Any],
    ) -> bool:
        """Check if two claims contradict."""
        polarity_a = claim_a.get("polarity", "neutral")
        polarity_b = claim_b.get("polarity", "neutral")

        # Check polarity conflict
        if (polarity_a, polarity_b) in self._contradiction_pairs or \
           (polarity_b, polarity_a) in self._contradiction_pairs:
            return True

        # Check for metric conflicts (same metric, different values)
        metric_a = claim_a.get("metric")
        metric_b = claim_b.get("metric")
        if metric_a and metric_b and metric_a == metric_b:
            value_a = claim_a.get("value")
            value_b = claim_b.get("value")
            if value_a and value_b and str(value_a) != str(value_b):
                return True

        return False

    def _get_contradiction_type(
        self,
        claim_a: Dict[str, Any],
        claim_b: Dict[str, Any],
    ) -> str:
        """Determine the type of contradiction."""
        polarity_a = claim_a.get("polarity", "neutral")
        polarity_b = claim_b.get("polarity", "neutral")

        if polarity_a != polarity_b and polarity_a != "neutral" and polarity_b != "neutral":
            return "polarity_conflict"

        if claim_a.get("metric") and claim_b.get("metric"):
            return "metric_conflict"

        return "general_conflict"

    def _calculate_severity(
        self,
        claim_a: Dict[str, Any],
        claim_b: Dict[str, Any],
    ) -> float:
        """Calculate contradiction severity (0-1)."""
        severity = 0.5  # Base severity

        # Higher confidence claims = more severe contradiction
        conf_a = claim_a.get("confidence", 0.5)
        conf_b = claim_b.get("confidence", 0.5)
        severity += 0.3 * (conf_a + conf_b) / 2

        # Polarity conflicts are more severe
        if claim_a.get("polarity") != claim_b.get("polarity"):
            severity += 0.2

        return min(1.0, severity)

    def _generate_resolution_hint(
        self,
        claim_a: Dict[str, Any],
        claim_b: Dict[str, Any],
    ) -> str:
        """Generate a hint for resolving the contradiction."""
        return (
            f"Need additional evidence to reconcile: "
            f"'{claim_a.get('text', '')[:50]}...' vs "
            f"'{claim_b.get('text', '')[:50]}...'"
        )

    def _hash_claim(self, claim: Dict[str, Any]) -> str:
        """Generate a short hash for a claim."""
        import hashlib
        text = claim.get("text", "")
        return hashlib.sha256(text.encode()).hexdigest()[:12]
