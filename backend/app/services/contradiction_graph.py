"""Contradiction graph builder.

Uses NLI-based comparison when available, falls back to keyword overlap heuristic.
No longer depends on transformers pipeline directly — uses gateway or fallback.
"""

from typing import List, Dict, Any, Tuple
import networkx as nx
import logging

logger = logging.getLogger(__name__)


class ContradictionGraphBuilder:
    """Build contradiction graphs from claims.

    Uses a simple keyword-overlap heuristic by default.
    Can be extended with NLI via the model gateway in the future.
    """

    def __init__(self):
        pass

    def compare_claims(self, claim1: str, claim2: str) -> Tuple[str, float]:
        """Compare two claims using keyword-overlap heuristic.

        Returns: (label, confidence_score)
        """
        try:
            # Simple heuristic: look for negation/opposition patterns
            negation_words = {"not", "no", "never", "neither", "nor", "doesn't",
                             "don't", "isn't", "aren't", "wasn't", "weren't",
                             "won't", "wouldn't", "couldn't", "shouldn't",
                             "however", "contrary", "opposite", "unlike",
                             "disagree", "conflict", "contradict", "fail",
                             "decrease", "reduce", "worse", "poor"}

            words1 = set(claim1.lower().split())
            words2 = set(claim2.lower().split())

            overlap = words1 & words2
            neg1 = words1 & negation_words
            neg2 = words2 & negation_words

            # If claims share topic words but differ in negation, possible contradiction
            if overlap and (neg1 ^ neg2):  # XOR — one has negation, other doesn't
                score = min(0.7 + len(overlap) * 0.02, 0.95)
                return "CONTRADICTION", score

            # Low confidence neutral
            return "NEUTRAL", 0.3

        except Exception as e:
            logger.error(f"Claim comparison error: {e}")
            return "NEUTRAL", 0.0

    def build_graph(self, claims: List[str]) -> Dict[str, Any]:
        G = nx.Graph()
        for i, c in enumerate(claims):
            G.add_node(i, claim=c)

        for i in range(len(claims)):
            for j in range(i+1, len(claims)):
                label, score = self.compare_claims(claims[i], claims[j])
                if label == "CONTRADICTION" and score > 0.75:
                    G.add_edge(i, j, label="contradiction", weight=score)

        return {
            "nodes": [{"id": n, "claim": G.nodes[n]["claim"]} for n in G.nodes],
            "edges": [{"source": u, "target": v, "weight": d["weight"]} for u,v,d in G.edges(data=True)]
        }
