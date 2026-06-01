"""Bridge discovery between distant concepts."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.services.graph.repository import GraphRepository
from app.services.graph.neo4j_client import get_neo4j_client

logger = logging.getLogger(__name__)


class BridgeFinder:
    """Finds bridge paths between distant concepts."""

    def __init__(self, repository: Optional[GraphRepository] = None):
        """Initialize bridge finder.

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

    async def find_bridges(
        self,
        source_entities: List[str],
        target_entities: List[str],
        max_hops: int = 4,
        min_novelty: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """Find bridge paths between source and target entities.

        Args:
            source_entities: List of source entity keys
            target_entities: List of target entity keys
            max_hops: Maximum path length
            min_novelty: Minimum novelty score

        Returns:
            List of bridge candidates
        """
        if not await self._ensure_connected():
            return []

        bridges = []

        for source in source_entities:
            for target in target_entities:
                if source == target:
                    continue

                paths = await self.repository.find_bridge_paths(
                    source, target, max_hops
                )

                for path in paths:
                    novelty = self._calculate_novelty(path, source, target)
                    if novelty >= min_novelty:
                        bridges.append({
                            "source": source,
                            "target": target,
                            "path": path.dict(),
                            "novelty_score": novelty,
                            "path_length": path.length,
                            "bridge_type": self._classify_bridge(path),
                        })

        # Sort by novelty
        bridges.sort(key=lambda x: x["novelty_score"], reverse=True)
        return bridges

    def _calculate_novelty(
        self,
        path: Any,
        source: str,
        target: str,
    ) -> float:
        """Calculate novelty of a bridge path."""
        novelty = 0.5  # Base novelty

        # Longer paths are more novel
        length = path.length if hasattr(path, "length") else len(path.nodes)
        if length >= 3:
            novelty += 0.2
        if length >= 4:
            novelty += 0.1

        # Check if intermediate nodes are from different domains
        nodes = path.nodes if hasattr(path, "nodes") else []
        domains = set()
        for node in nodes:
            node_type = node.get("type", "") if isinstance(node, dict) else ""
            if node_type:
                domains.add(node_type)

        if len(domains) >= 3:
            novelty += 0.2  # Cross-domain bridge

        return min(1.0, novelty)

    def _classify_bridge(self, path: Any) -> str:
        """Classify the type of bridge."""
        nodes = path.nodes if hasattr(path, "nodes") else []

        # Check for shared methods
        method_count = sum(
            1 for n in nodes
            if isinstance(n, dict) and n.get("type") == "METHOD"
        )

        if method_count >= 2:
            return "shared_method"

        # Check for cross-domain
        types = set(
            n.get("type", "")
            for n in nodes
            if isinstance(n, dict)
        )

        if len(types) >= 3:
            return "cross_domain"

        return "conceptual_link"

    async def find_weak_connections(
        self,
        min_evidence: int = 2,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Find weakly connected entity pairs (potential gaps).

        Args:
            min_evidence: Minimum evidence count
            limit: Maximum results

        Returns:
            List of weak connection candidates
        """
        if not await self._ensure_connected():
            return []

        gaps = await self.repository.find_gaps(limit=limit)
        return gaps

    async def find_cross_domain_opportunities(
        self,
        domain_a: Optional[str] = None,
        domain_b: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Find cross-domain research opportunities.

        Args:
            domain_a: Optional first domain (entity type)
            domain_b: Optional second domain

        Returns:
            List of cross-domain opportunities
        """
        if not await self._ensure_connected():
            return []

        # Get trending entities in each domain
        trending = await self.repository.find_trending_concepts(days=365, limit=50)

        # Group by type
        by_type: Dict[str, List[Dict]] = {}
        for entity in trending:
            entity_type = entity.get("entity_type", "UNKNOWN")
            if entity_type not in by_type:
                by_type[entity_type] = []
            by_type[entity_type].append(entity)

        opportunities = []

        # Find pairs of types that don't often interact
        types = list(by_type.keys())
        for i, type_a in enumerate(types):
            for type_b in types[i + 1:]:
                if domain_a and type_a != domain_a:
                    continue
                if domain_b and type_b != domain_b:
                    continue

                # Check for entities that could benefit from cross-pollination
                entities_a = by_type[type_a][:5]
                entities_b = by_type[type_b][:5]

                for ea in entities_a:
                    for eb in entities_b:
                        opportunities.append({
                            "entity_a": ea,
                            "entity_b": eb,
                            "type_a": type_a,
                            "type_b": type_b,
                            "opportunity_type": "cross_domain_transfer",
                        })

        return opportunities[:20]
