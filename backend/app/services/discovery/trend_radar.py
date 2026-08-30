"""Trend detection and radar."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.services.graph.repository import GraphRepository
from app.services.graph.neo4j_client import get_neo4j_client

logger = logging.getLogger(__name__)


class TrendRadar:
    """Detects emerging trends and weak signals."""

    def __init__(self, repository: Optional[GraphRepository] = None):
        """Initialize trend radar.

        Args:
            repository: Optional GraphRepository instance
        """
        self.repository = repository or GraphRepository(get_neo4j_client())
        self._connected = False

    async def _ensure_connected(self) -> bool:
        """Ensure connection to Neo4j."""
        try:
            client = self.repository.client
            if not client.is_connected:
                await client.connect()
            self._connected = True
            return True
        except Exception as e:
            logger.warning(f"Neo4j connection failed: {e}")
            self._connected = False
            return False

    async def find_trending_entities(
        self,
        days: int = 365,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Find trending entities based on recent mentions.

        Args:
            days: Time window in days
            limit: Maximum results

        Returns:
            List of trending entities with metrics
        """
        if not await self._ensure_connected():
            return []

        trending = await self.repository.find_trending_concepts(days=days, limit=limit)

        # Add trend classification
        for entity in trending:
            doc_count = entity.get("document_count", 0)
            mention_count = entity.get("mention_count", 0)

            # Classify trend strength
            if doc_count >= 10 and mention_count >= 20:
                entity["trend_strength"] = "strong"
            elif doc_count >= 5 and mention_count >= 10:
                entity["trend_strength"] = "moderate"
            else:
                entity["trend_strength"] = "emerging"

        return trending

    async def detect_weak_signals(
        self,
        min_docs: int = 2,
        max_docs: int = 5,
        limit: int = 15,
    ) -> List[Dict[str, Any]]:
        """Detect weak signals - emerging concepts with low but growing attention.

        Args:
            min_docs: Minimum document count
            max_docs: Maximum document count
            limit: Maximum results

        Returns:
            List of weak signal candidates
        """
        if not await self._ensure_connected():
            return []

        # Get entities with low document counts but recent activity
        trending = await self.repository.find_trending_concepts(days=180, limit=50)

        weak_signals = []
        for entity in trending:
            doc_count = entity.get("document_count", 0)
            if min_docs <= doc_count <= max_docs:
                entity["signal_type"] = "emerging_concept"
                entity["watch_priority"] = "high" if doc_count == max_docs else "medium"
                weak_signals.append(entity)

        return weak_signals[:limit]

    async def find_rising_methods(
        self,
        time_window_days: int = 365,
    ) -> List[Dict[str, Any]]:
        """Find methods with increasing usage over time.

        Args:
            time_window_days: Time window to analyze

        Returns:
            List of rising methods
        """
        if not await self._ensure_connected():
            return []

        # Get all METHOD entities sorted by recent activity
        trending = await self.repository.find_trending_concepts(
            days=time_window_days,
            limit=30,
        )

        rising = [
            e for e in trending
            if e.get("entity_type") == "METHOD"
        ]

        # Sort by document count as proxy for adoption
        rising.sort(key=lambda x: x.get("document_count", 0), reverse=True)

        return rising[:15]

    async def get_field_overview(
        self,
        entity_type: Optional[str] = None,
        days: int = 365,
    ) -> Dict[str, Any]:
        """Get overview of a research field.

        Args:
            entity_type: Optional entity type filter
            days: Time window

        Returns:
            Field overview with top entities and trends
        """
        if not await self._ensure_connected():
            return {"error": "Neo4j not connected"}

        trending = await self.repository.find_trending_concepts(days=days, limit=50)

        if entity_type:
            trending = [e for e in trending if e.get("entity_type") == entity_type]

        # Group by type
        by_type: Dict[str, List[Dict]] = {}
        for entity in trending:
            etype = entity.get("entity_type", "UNKNOWN")
            if etype not in by_type:
                by_type[etype] = []
            by_type[etype].append(entity)

        return {
            "time_window_days": days,
            "total_entities": len(trending),
            "by_type": {
                etype: {
                    "count": len(entities),
                    "top": entities[:5],
                }
                for etype, entities in by_type.items()
            },
        }

    async def compare_time_periods(
        self,
        period1_days: int = 365,
        period2_days: int = 180,
    ) -> Dict[str, Any]:
        """Compare entity activity between two time periods.

        Args:
            period1_days: Longer period (e.g., 365 days)
            period2_days: Shorter period (e.g., 180 days)

        Returns:
            Comparison showing rising and declining entities
        """
        if not await self._ensure_connected():
            return {"error": "Neo4j not connected"}

        # Get trending for both periods
        trending1 = await self.repository.find_trending_concepts(days=period1_days, limit=50)
        trending2 = await self.repository.find_trending_concepts(days=period2_days, limit=50)

        # Create lookup by entity key
        lookup1 = {e.get("entity_key", ""): e for e in trending1}
        lookup2 = {e.get("entity_key", ""): e for e in trending2}

        rising = []
        declining = []
        stable = []

        for key, entity2 in lookup2.items():
            entity1 = lookup1.get(key)
            if not entity1:
                # New entity in recent period
                entity2["trend_direction"] = "new"
                rising.append(entity2)
                continue

            count1 = entity1.get("document_count", 0)
            count2 = entity2.get("document_count", 0)

            # Normalize by time period
            rate1 = count1 / period1_days
            rate2 = count2 / period2_days

            if rate2 > rate1 * 1.2:
                entity2["trend_direction"] = "rising"
                entity2["growth_rate"] = rate2 / rate1 if rate1 > 0 else float("inf")
                rising.append(entity2)
            elif rate2 < rate1 * 0.8:
                entity2["trend_direction"] = "declining"
                declining.append(entity2)
            else:
                entity2["trend_direction"] = "stable"
                stable.append(entity2)

        return {
            "rising": sorted(rising, key=lambda x: x.get("growth_rate", 0), reverse=True)[:10],
            "declining": declining[:10],
            "stable": stable[:10],
            "new": [e for e in rising if e.get("trend_direction") == "new"][:10],
        }
