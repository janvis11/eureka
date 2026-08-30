"""Query planner for hybrid retrieval."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List


class QueryIntent(str, Enum):
    """Query intent types."""
    FACT_LOOKUP = "fact_lookup"
    COMPARE = "compare"
    GLOBAL_SUMMARY = "global_summary"
    CONTRADICTION_SEARCH = "contradiction_search"
    GAP_SEARCH = "gap_search"
    HYPOTHESIS_REQUEST = "hypothesis_request"
    TREND_SEARCH = "trend_search"
    GRAPH_PATH_REQUEST = "graph_path_request"


@dataclass
class QueryPlan:
    """Retrieval plan for a query."""
    intent: QueryIntent
    entities: List[str] = field(default_factory=list)
    retrievers: List[str] = field(default_factory=list)
    needs_global_context: bool = False
    needs_counter_evidence: bool = False
    needs_graph_paths: bool = False
    confidence: float = 0.0


class QueryPlanner:
    """Plans retrieval strategy based on query intent."""

    # Intent keywords
    INTENT_PATTERNS = {
        QueryIntent.FACT_LOOKUP: [
            r"\bwhat is\b", r"\bdefine\b", r"\bmeaning of\b",
            r"\bwho is\b", r"\bwhen did\b", r"\bwhere is\b",
        ],
        QueryIntent.COMPARE: [
            r"\bcompare\b", r"\bvs\b", r"\bversus\b", r"\bdifference between\b",
            r"\bsimilar to\b", r"\bbetter than\b",
        ],
        QueryIntent.GLOBAL_SUMMARY: [
            r"\bsummarize\b", r"\boverview of\b", r"\btell me about\b",
            r"\bwhat do we know about\b", r"\bstate of\b",
        ],
        QueryIntent.CONTRADICTION_SEARCH: [
            r"\bcontradict\b", r"\bdisagree\b", r"\bconflict\b",
            r"\bdebate\b", r"\bcontroversy\b",
        ],
        QueryIntent.GAP_SEARCH: [
            r"\bgap\b", r"\bopen question\b", r"\bunknown\b",
            r"\bnot yet\b", r"\bfuture work\b", r"\bchallenge\b",
        ],
        QueryIntent.HYPOTHESIS_REQUEST: [
            r"\bhypothesis\b", r"\bpredict\b", r"\bwhat if\b",
            r"\bcould\b", r"\bmight\b",
        ],
        QueryIntent.TREND_SEARCH: [
            r"\btrend\b", r"\bremerging\b", r"\bris ing\b",
            r"\bgrowing\b", r"\brecent\b", r"\blatest\b",
        ],
        QueryIntent.GRAPH_PATH_REQUEST: [
            r"\bconnect\b", r"\brelate\b", r"\bpath between\b",
            r"\blink between\b", r"\brelationship between\b",
        ],
    }

    # Entity extraction patterns
    ENTITY_PATTERNS = [
        r'"([^"]+)"',  # Quoted phrases
        r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',  # Title case phrases
    ]

    def plan(self, query: str) -> QueryPlan:
        """Create a retrieval plan for the query."""
        intent = self._detect_intent(query)
        entities = self._extract_entities(query)
        retrievers = self._select_retrievers(intent)

        needs_global = intent in {
            QueryIntent.GLOBAL_SUMMARY,
            QueryIntent.TREND_SEARCH,
            QueryIntent.GAP_SEARCH,
        }
        needs_counter = intent in {
            QueryIntent.CONTRADICTION_SEARCH,
            QueryIntent.COMPARE,
        }
        needs_paths = intent in {
            QueryIntent.GRAPH_PATH_REQUEST,
            QueryIntent.COMPARE,
        }

        return QueryPlan(
            intent=intent,
            entities=entities,
            retrievers=retrievers,
            needs_global_context=needs_global,
            needs_counter_evidence=needs_counter,
            needs_graph_paths=needs_paths,
            confidence=self._calculate_confidence(query, intent),
        )

    def _detect_intent(self, query: str) -> QueryIntent:
        """Detect the intent of the query."""
        query_lower = query.lower()
        scores = {}

        for intent, patterns in self.INTENT_PATTERNS.items():
            score = sum(1 for p in patterns if re.search(p, query_lower))
            scores[intent] = score

        if not any(scores.values()):
            return QueryIntent.FACT_LOOKUP

        return max(scores, key=scores.get)

    def _extract_entities(self, query: str) -> List[str]:
        """Extract entity mentions from the query."""
        entities = []

        # Extract quoted phrases first
        quoted = re.findall(r'"([^"]+)"', query)
        entities.extend(quoted)

        # Extract title case phrases (potential named entities)
        title_case = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', query)
        entities.extend(title_case)

        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for e in entities:
            if e.lower() not in seen and len(e) > 2:
                seen.add(e.lower())
                unique.append(e)

        return unique[:5]  # Limit to top 5 entities

    def _select_retrievers(self, intent: QueryIntent) -> List[str]:
        """Select which retrievers to use based on intent."""
        retriever_map = {
            QueryIntent.FACT_LOOKUP: ["bm25", "vector"],
            QueryIntent.COMPARE: ["bm25", "vector", "graph"],
            QueryIntent.GLOBAL_SUMMARY: ["vector", "graph"],
            QueryIntent.CONTRADICTION_SEARCH: ["bm25", "vector", "graph"],
            QueryIntent.GAP_SEARCH: ["vector", "graph"],
            QueryIntent.HYPOTHESIS_REQUEST: ["vector", "graph"],
            QueryIntent.TREND_SEARCH: ["vector", "graph"],
            QueryIntent.GRAPH_PATH_REQUEST: ["graph"],
        }
        return retriever_map.get(intent, ["bm25", "vector"])

    def _calculate_confidence(self, query: str, intent: QueryIntent) -> float:
        """Calculate confidence in the query plan."""
        # Simple heuristic: longer queries with clear intent are more confident
        length_score = min(1.0, len(query) / 100)
        intent_score = 0.5  # Base confidence

        # Boost if we detected entities
        entity_bonus = 0.2

        return min(1.0, intent_score + length_score * 0.3 + entity_bonus)
