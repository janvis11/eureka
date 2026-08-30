"""Graph-based retriever using Neo4j."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.services.graph.repository import GraphRepository
from app.services.graph.neo4j_client import get_neo4j_client

logger = logging.getLogger(__name__)


class GraphRetriever:
    """Graph-based retrieval using Neo4j."""

    def __init__(self, repository: Optional[GraphRepository] = None):
        """Initialize graph retriever.

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

    async def retrieve_by_entity(
        self,
        entity_key: str,
        hops: int = 2,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """Retrieve documents and claims related to an entity.

        Args:
            entity_key: Entity key to search around
            hops: Number of hops for neighborhood expansion
            top_k: Maximum number of results

        Returns:
            List of results with provenance
        """
        if not await self._ensure_connected():
            return []

        results = []

        try:
            # Get claims about the entity
            claims = await self.repository.get_claims_by_entity(entity_key, limit=top_k)
            for claim in claims:
                results.append({
                    "type": "claim",
                    "text": claim.get("text", ""),
                    "claim_type": claim.get("claim_type", ""),
                    "polarity": claim.get("polarity", ""),
                    "confidence": claim.get("confidence", 0.0),
                    "score": claim.get("confidence", 0.0),
                    "retriever": "graph",
                    "entity_key": entity_key,
                })

            # Get related documents
            docs = await self.repository.get_related_documents(entity_key, limit=top_k // 2)
            for doc in docs:
                results.append({
                    "type": "document",
                    "text": doc.get("title", ""),
                    "doc_id": doc.get("id", ""),
                    "source_type": doc.get("source_type", ""),
                    "score": 0.8,  # Default score for documents
                    "retriever": "graph",
                    "entity_key": entity_key,
                })

        except Exception as e:
            logger.error(f"Graph retrieval failed: {e}")

        return results[:top_k]

    async def find_bridge_paths(
        self,
        source_entity: str,
        target_entity: str,
        max_hops: int = 4,
    ) -> List[Dict[str, Any]]:
        """Find paths between two entities.

        Args:
            source_entity: Source entity key
            target_entity: Target entity key
            max_hops: Maximum path length

        Returns:
            List of paths with nodes and relationships
        """
        if not await self._ensure_connected():
            return []

        try:
            paths = await self.repository.find_bridge_paths(
                source_entity, target_entity, max_hops
            )
            return [p.dict() for p in paths]
        except Exception as e:
            logger.error(f"Bridge path finding failed: {e}")
            return []

    async def find_contradictions(
        self,
        entity_key: str,
    ) -> List[Dict[str, Any]]:
        """Find contradictory claims about an entity.

        Args:
            entity_key: Entity to search for contradictions

        Returns:
            List of contradiction candidates
        """
        if not await self._ensure_connected():
            return []

        try:
            contradictions = await self.repository.find_contradictory_claims(entity_key)
            return [c.dict() for c in contradictions]
        except Exception as e:
            logger.error(f"Contradiction search failed: {e}")
            return []

    async def get_trending_entities(
        self,
        days: int = 365,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get trending entities based on recent mentions.

        Args:
            days: Time window in days
            limit: Maximum number of results

        Returns:
            List of trending entities with metrics
        """
        if not await self._ensure_connected():
            return []

        try:
            return await self.repository.find_trending_concepts(days=days, limit=limit)
        except Exception as e:
            logger.error(f"Trend search failed: {e}")
            return []

    async def get_underexplored_gaps(
        self,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Find underexplored connections between entities.

        Args:
            limit: Maximum number of results

        Returns:
            List of gap candidates
        """
        if not await self._ensure_connected():
            return []

        try:
            return await self.repository.find_gaps(limit=limit)
        except Exception as e:
            logger.error(f"Gap search failed: {e}")
            return []

    async def search_by_keyword(
        self,
        keyword: str,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search for entities by keyword match.

        Args:
            keyword: Keyword to search for
            top_k: Maximum number of results

        Returns:
            List of matching entities
        """
        if not await self._ensure_connected():
            return []

        # Simple keyword search in entity names
        # In production, use Neo4j full-text index
        query = """
        MATCH (e:Entity)
        WHERE toLower(e.name) CONTAINS toLower($keyword)
           OR toLower(e.description) CONTAINS toLower($keyword)
        RETURN e.key AS key, e.name AS name, e.type AS type,
               e.description AS description
        LIMIT $limit
        """

        try:
            client = self.repository.client
            results = await client.execute_query(query, {"keyword": keyword, "limit": top_k})
            return [
                {
                    "type": "entity",
                    "entity_key": r.get("key", ""),
                    "name": r.get("name", ""),
                    "entity_type": r.get("type", ""),
                    "description": r.get("description", ""),
                    "score": 1.0,
                    "retriever": "graph",
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []
