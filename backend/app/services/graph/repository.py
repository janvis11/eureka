"""Graph repository for Neo4j operations."""

from __future__ import annotations

import logging
import json
import uuid
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.services.graph.neo4j_client import Neo4jClient, get_neo4j_client
from app.services.graph.queries import (
    UPSERT_DOCUMENT,
    UPSERT_CHUNK,
    UPSERT_ENTITY,
    UPSERT_CLAIM,
    LINK_CLAIM_TO_ENTITIES,
    LINK_CHUNK_TO_ENTITIES,
    GET_NEIGHBORHOOD,
    GET_GRAPH_OVERVIEW,
    FIND_BRIDGE_PATHS,
    FIND_GAPS,
    FIND_CONTRADICTIONS,
    GET_CLAIMS_BY_ENTITY,
    GET_RELATED_DOCUMENTS,
    COMMUNITY_DETECTION,
    FIND_TRENDING,
    UPSERT_HYPOTHESIS,
    LINK_HYPOTHESIS_CLAIMS,
    UPSERT_GAP,
    UPSERT_ENTITY_RELATION,
)
from app.services.graph.schema import (
    DocumentGraphPayload,
    ChunkGraphPayload,
    EntityPayload,
    ClaimPayload,
    GraphNeighborhood,
    GraphPath,
    ContradictionCandidate,
    HypothesisPayload,
    ResearchGapPayload,
)

logger = logging.getLogger(__name__)


class GraphRepository:
    """Repository for Neo4j graph operations."""

    def __init__(self, client: Optional[Neo4jClient] = None):
        self.client = client or get_neo4j_client()

    def _slug_entity_value(self, value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")

    async def initialize_schema(self) -> None:
        """Initialize graph schema with constraints."""
        await self.client.initialize_schema()

    async def resolve_entity_key(self, value: str) -> Optional[str]:
        """Resolve a user-entered entity name/key to the canonical graph key."""
        raw = (value or "").strip()
        if not raw:
            return None

        slug_prefix = f"{self._slug_entity_value(raw.split(':', 1)[0])}:"
        results = await self.client.execute_query(
            """
            MATCH (e:Entity)
            WHERE toLower(e.key) = toLower($raw)
               OR toLower(e.name) = toLower($raw)
               OR toLower(e.key) STARTS WITH $slug_prefix
            RETURN e.key AS key
            ORDER BY size(e.name) ASC
            LIMIT 1
            """,
            {"raw": raw, "slug_prefix": slug_prefix},
        )
        return results[0].get("key") if results else None

    async def upsert_document(self, doc: DocumentGraphPayload) -> str:
        """Upsert a document node."""
        result = await self.client.execute_write(
            UPSERT_DOCUMENT,
            {
                "id": doc.id,
                "title": doc.title,
                "source_type": doc.source_type,
                "created_at": doc.created_at,
                "metadata_json": json.dumps(doc.metadata or {}, default=str),
            },
        )
        return result.get("d.id", doc.id)

    async def upsert_chunk(self, chunk: ChunkGraphPayload) -> str:
        """Upsert a chunk node and link to document."""
        result = await self.client.execute_write(
            UPSERT_CHUNK,
            {
                "id": chunk.id,
                "document_id": chunk.document_id,
                "text": chunk.text,
                "chunk_index": chunk.chunk_index,
                "token_count": chunk.token_count,
                "source_span_start": chunk.source_span_start,
                "source_span_end": chunk.source_span_end,
            },
        )
        return result.get("c.id", chunk.id)

    async def upsert_entity(self, entity: EntityPayload) -> str:
        """Upsert an entity node."""
        result = await self.client.execute_write(
            UPSERT_ENTITY,
            {
                "key": entity.key,
                "name": entity.name,
                "type": entity.type,
                "aliases": entity.aliases,
                "description": entity.description,
            },
        )
        return result.get("e.key", entity.key)

    async def upsert_claim(self, claim: ClaimPayload) -> str:
        """Upsert a claim node."""
        result = await self.client.execute_write(
            UPSERT_CLAIM,
            {
                "id": claim.id,
                "text": claim.text,
                "claim_type": claim.claim_type,
                "polarity": claim.polarity,
                "confidence": claim.confidence,
                "source_quote": claim.source_quote,
                "chunk_id": claim.chunk_id,
            },
        )
        return result.get("c.id", claim.id)

    async def link_claim_to_entities(
        self, claim_id: str, entity_keys: List[str]
    ) -> int:
        """Link a claim to its entities."""
        result = await self.client.execute_write(
            LINK_CLAIM_TO_ENTITIES,
            {"claim_id": claim_id, "entity_keys": entity_keys},
        )
        return len(entity_keys)

    async def link_chunk_to_entities(
        self, chunk_id: str, entity_keys: List[str]
    ) -> int:
        """Link a chunk to mentioned entities."""
        await self.client.execute_write(
            LINK_CHUNK_TO_ENTITIES,
            {"chunk_id": chunk_id, "entity_keys": entity_keys},
        )
        return len(entity_keys)

    async def upsert_entity_relation(
        self,
        source_key: str,
        target_key: str,
        predicate: str,
        evidence: str,
        confidence: float,
        chunk_id: str,
        source_quote: str = "",
    ) -> str:
        """Upsert a provenance-rich relationship between two entities."""
        if source_key == target_key:
            return ""

        result = await self.client.execute_write(
            UPSERT_ENTITY_RELATION,
            {
                "source_key": source_key,
                "target_key": target_key,
                "predicate": predicate,
                "evidence": evidence[:1000] if evidence else "",
                "confidence": float(confidence),
                "chunk_id": chunk_id,
                "source_quote": source_quote[:1000] if source_quote else evidence[:1000],
            },
        )
        relationship_id = result.get("relationship_id")
        return str(relationship_id) if relationship_id is not None else ""

    async def get_neighborhood(
        self, entity_key: str, hops: int = 2
    ) -> GraphNeighborhood:
        """Get the neighborhood of an entity."""
        results = await self.client.execute_query(
            GET_NEIGHBORHOOD,
            {"entity_key": entity_key, "hops": hops},
        )

        nodes = []
        edges = []

        if results:
            row = results[0]
            center = row.get("center", {})
            neighbor_nodes = row.get("nodes", [])
            edge_data = row.get("edges", [])

            nodes = [dict(center)] if center else []
            nodes.extend([dict(n) for n in neighbor_nodes if n])

            for edge in edge_data:
                if edge:
                    edges.append(
                        {
                            "start": str(edge.get("start", {}).get("key", "")),
                            "type": edge.get("type", ""),
                            "end": str(edge.get("end", {}).get("key", "")),
                        }
                    )

        return GraphNeighborhood(
            center_key=entity_key,
            nodes=nodes,
            edges=[e for e in edges if e["start"] and e["end"]],
        )

    async def get_overview(
        self,
        limit: int = 50,
        relationship_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get a sampled graph for UI visualization."""
        normalized_types = [
            rel_type.strip().upper()
            for rel_type in (relationship_types or [])
            if rel_type and rel_type.strip()
        ]
        bounded_limit = max(1, min(int(limit), 100))

        results = await self.client.execute_query(
            GET_GRAPH_OVERVIEW,
            {
                "limit": bounded_limit,
                "relationship_types": normalized_types,
            },
        )

        if not results:
            return {
                "nodes": [],
                "edges": [],
                "relationship_types": normalized_types,
                "limit": bounded_limit,
            }

        row = results[0]
        nodes_by_id: Dict[str, Dict[str, Any]] = {}
        for node in row.get("nodes", []):
            if not node:
                continue
            node_id = str(node.get("id", "")).strip()
            if not node_id:
                continue
            nodes_by_id[node_id] = {
                key: value
                for key, value in dict(node).items()
                if value is not None and value != ""
            }

        edges = []
        for edge in row.get("edges", []):
            if not edge:
                continue
            edge_data = {
                key: value
                for key, value in dict(edge).items()
                if value is not None and value != ""
            }
            if edge_data.get("source") and edge_data.get("target"):
                edges.append(edge_data)

        return {
            "nodes": list(nodes_by_id.values()),
            "edges": edges,
            "relationship_types": normalized_types,
            "limit": bounded_limit,
        }

    async def find_bridge_paths(
        self, source_key: str, target_key: str, max_hops: int = 4
    ) -> List[GraphPath]:
        """Find paths between two entities."""
        results = await self.client.execute_query(
            FIND_BRIDGE_PATHS,
            {"source": source_key, "target": target_key, "max_hops": max_hops},
        )

        paths = []
        for row in results:
            path = row.get("path")
            if hasattr(path, "nodes") and hasattr(path, "relationships"):
                nodes = list(path.nodes)
                rels = list(path.relationships)
            elif isinstance(path, dict):
                nodes = path.get("nodes", [])
                rels = path.get("relationships", [])
            else:
                nodes = []
                rels = []

            paths.append(
                GraphPath(
                    nodes=[dict(n) for n in nodes if n],
                    relationships=[
                        {
                            **dict(r),
                            "type": getattr(r, "type", dict(r).get("type", "")),
                        }
                        for r in rels
                        if r
                    ],
                    length=len(nodes) - 1 if nodes else 0,
                )
            )

        return paths

    async def find_contradictory_claims(
        self, entity_key: str
    ) -> List[ContradictionCandidate]:
        """Find potentially contradictory claims about an entity."""
        results = await self.client.execute_query(
            FIND_CONTRADICTIONS, {"entity_key": entity_key}
        )

        contradictions = []
        for row in results:
            contradictions.append(
                ContradictionCandidate(
                    entity_key=entity_key,
                    claim_a_id=row.get("claim_a_id", ""),
                    claim_a_text=row.get("claim_a_text", ""),
                    claim_b_id=row.get("claim_b_id", ""),
                    claim_b_text=row.get("claim_b_text", ""),
                    contradiction_score=row.get("contradiction_score", 0.0),
                )
            )

        return contradictions

    async def find_gaps(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Find underexplored connections between entities."""
        results = await self.client.execute_query(FIND_GAPS)
        return results[:limit]

    async def get_claims_by_entity(
        self, entity_key: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get claims about an entity."""
        results = await self.client.execute_query(
            GET_CLAIMS_BY_ENTITY,
            {"entity_key": entity_key, "limit": limit},
        )

        claims = []
        for row in results:
            claim = row.get("c", {})
            claims.append(
                {
                    "id": claim.get("id", ""),
                    "text": claim.get("text", ""),
                    "claim_type": claim.get("claim_type", ""),
                    "polarity": claim.get("polarity", ""),
                    "confidence": claim.get("confidence", 0.0),
                }
            )

        return claims

    async def get_related_documents(
        self, entity_key: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get documents related to an entity."""
        results = await self.client.execute_query(
            GET_RELATED_DOCUMENTS,
            {"entity_key": entity_key, "limit": limit},
        )

        docs = []
        for row in results:
            doc = row.get("d", {})
            docs.append(
                {
                    "id": doc.get("id", ""),
                    "title": doc.get("title", ""),
                    "source_type": doc.get("source_type", ""),
                    "created_at": doc.get("created_at", ""),
                }
            )

        return docs

    async def detect_communities(self) -> List[Dict[str, Any]]:
        """Detect communities in the entity graph using Louvain."""
        try:
            results = await self.client.execute_query(COMMUNITY_DETECTION)
            return [
                {
                    "entity_key": row.get("entity_key", ""),
                    "community_id": row.get("communityId", 0),
                }
                for row in results
            ]
        except Exception as e:
            logger.error(f"Community detection failed: {e}")
            return []

    async def find_trending_concepts(
        self, days: int = 365, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Find trending concepts based on recent mentions."""
        results = await self.client.execute_query(
            FIND_TRENDING, {"days": days, "limit": limit}
        )
        return results

    async def upsert_hypothesis(self, hyp: HypothesisPayload) -> str:
        """Upsert a hypothesis node."""
        result = await self.client.execute_write(
            UPSERT_HYPOTHESIS,
            {
                "id": hyp.id,
                "text": hyp.text,
                "novelty_score": hyp.novelty_score,
                "feasibility_score": hyp.feasibility_score,
                "falsifiability_score": hyp.falsifiability_score,
                "evidence_count": hyp.evidence_count,
                "experiment_plan": hyp.experiment_plan,
            },
        )

        # Link to claims
        if hyp.supporting_claim_ids or hyp.counter_claim_ids:
            await self.client.execute_write(
                LINK_HYPOTHESIS_CLAIMS,
                {
                    "hypothesis_id": hyp.id,
                    "supporting_ids": hyp.supporting_claim_ids,
                    "counter_ids": hyp.counter_claim_ids,
                },
            )

        return result.get("h.id", hyp.id)

    async def vote_hypothesis(self, hypothesis_id: str, direction: str) -> Optional[Dict[str, int]]:
        """Increment votes on a graph hypothesis and return current totals."""
        vote_field = "votes_up" if direction == "up" else "votes_down"
        result = await self.client.execute_write(
            f"""
            MATCH (h:Hypothesis {{id: $id}})
            SET h.{vote_field} = coalesce(h.{vote_field}, 0) + 1,
                h.votes_up = coalesce(h.votes_up, 0),
                h.votes_down = coalesce(h.votes_down, 0)
            RETURN h.id AS id, h.votes_up AS votes_up, h.votes_down AS votes_down
            """,
            {"id": hypothesis_id},
        )

        if not result:
            return None

        return {
            "votes_up": int(result.get("votes_up", 0) or 0),
            "votes_down": int(result.get("votes_down", 0) or 0),
        }

    async def delete_document(self, document_id: str) -> Dict[str, int]:
        """Delete a document and its provenance-owned graph nodes."""
        result = await self.client.execute_write(
            """
            MATCH (d:Document {id: $id})
            OPTIONAL MATCH (d)-[:CONTAINS]->(chunk:Chunk)
            OPTIONAL MATCH (chunk)-[:ASSERTS]->(claim:Claim)
            WITH d, collect(DISTINCT chunk) AS chunks, collect(DISTINCT claim) AS claims
            DETACH DELETE d
            WITH chunks, claims, size(chunks) AS chunks_deleted, size(claims) AS claims_deleted
            FOREACH (claim IN claims | DETACH DELETE claim)
            FOREACH (chunk IN chunks | DETACH DELETE chunk)
            WITH chunks_deleted, claims_deleted
            OPTIONAL MATCH (entity:Entity)
            WHERE NOT EXISTS { MATCH (:Chunk)-[:MENTIONS]->(entity) }
              AND NOT EXISTS { MATCH (:Claim)-[:ABOUT]->(entity) }
              AND NOT EXISTS { MATCH (entity)-[:RELATED]-(:Entity) }
            WITH chunks_deleted,
                 claims_deleted,
                 [entity IN collect(entity) WHERE entity IS NOT NULL] AS orphan_entities
            FOREACH (entity IN orphan_entities | DETACH DELETE entity)
            RETURN 1 AS documents_deleted,
                   chunks_deleted,
                   claims_deleted,
                   size(orphan_entities) AS orphan_entities_deleted
            """,
            {"id": document_id},
        )

        return {
            "documents_deleted": int(result.get("documents_deleted", 0) or 0),
            "chunks_deleted": int(result.get("chunks_deleted", 0) or 0),
            "claims_deleted": int(result.get("claims_deleted", 0) or 0),
            "orphan_entities_deleted": int(result.get("orphan_entities_deleted", 0) or 0),
        }

    async def upsert_research_gap(self, gap: ResearchGapPayload) -> str:
        """Upsert a research gap node."""
        result = await self.client.execute_write(
            UPSERT_GAP,
            {
                "id": gap.id,
                "description": gap.description,
                "entity_keys": gap.entity_keys,
                "evidence_count": gap.evidence_count,
                "weakness_score": gap.weakness_score,
            },
        )
        return result.get("g.id", gap.id)

    async def get_stats(self) -> Dict[str, int]:
        """Get graph statistics."""
        queries = {
            "documents": "MATCH (d:Document) RETURN count(d) AS count",
            "chunks": "MATCH (c:Chunk) RETURN count(c) AS count",
            "entities": "MATCH (e:Entity) RETURN count(e) AS count",
            "claims": "MATCH (c:Claim) RETURN count(c) AS count",
            "hypotheses": "MATCH (h:Hypothesis) RETURN count(h) AS count",
            "relationships": "MATCH ()-[r]->() RETURN count(r) AS count",
        }

        stats = {}
        for key, query in queries.items():
            results = await self.client.execute_query(query)
            stats[key] = results[0].get("count", 0) if results else 0

        return stats
