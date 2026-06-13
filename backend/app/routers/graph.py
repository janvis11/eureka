"""Neo4j Knowledge Graph API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel

from app.services.graph.repository import GraphRepository
from app.services.graph.neo4j_client import get_neo4j_client
from app.services.graph.schema import (
    EntityPayload,
    ClaimPayload,
    HypothesisPayload,
    ResearchGapPayload,
)

router = APIRouter(prefix="/graph", tags=["graph"])


def get_graph_repo() -> GraphRepository:
    """Get graph repository instance."""
    return GraphRepository(get_neo4j_client())


class PathRequest(BaseModel):
    """Request for finding paths between entities."""
    source: str
    target: str
    max_hops: int = 4


class EntityNeighborhoodResponse(BaseModel):
    """Response for entity neighborhood query."""
    center_key: str
    nodes: List[dict]
    edges: List[dict]


@router.get("/stats")
async def get_graph_stats(repo: GraphRepository = Depends(get_graph_repo)):
    """Get knowledge graph statistics."""
    try:
        stats = await repo.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph stats failed: {e}")


@router.get("/overview")
async def get_graph_overview(
    limit: int = Query(25, ge=1, le=100),
    relationship_types: Optional[str] = Query(
        None,
        description="Comma-separated relationship types, for example CONTAINS,MENTIONS",
    ),
    repo: GraphRepository = Depends(get_graph_repo),
):
    """Get a sampled graph overview for UI visualization."""
    try:
        selected_types = [
            value.strip().upper()
            for value in (relationship_types or "").split(",")
            if value.strip()
        ]
        return await repo.get_overview(
            limit=limit,
            relationship_types=selected_types,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph overview failed: {e}")


@router.get("/entities/{entity_key}/neighborhood", response_model=EntityNeighborhoodResponse)
async def get_entity_neighborhood(
    entity_key: str,
    hops: int = 2,
    repo: GraphRepository = Depends(get_graph_repo),
):
    """Get the neighborhood of an entity."""
    try:
        resolved_key = await repo.resolve_entity_key(entity_key) or entity_key
        neighborhood = await repo.get_neighborhood(resolved_key, hops=hops)
        return neighborhood
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/paths")
async def find_bridge_paths(
    request: PathRequest,
    repo: GraphRepository = Depends(get_graph_repo),
):
    """Find paths between two entities in the graph."""
    try:
        source_key = await repo.resolve_entity_key(request.source) or request.source
        target_key = await repo.resolve_entity_key(request.target) or request.target
        paths = await repo.find_bridge_paths(
            source_key, target_key, request.max_hops
        )
        return {"paths": [p.model_dump() for p in paths]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities/{entity_key}/contradictions")
async def get_entity_contradictions(
    entity_key: str,
    repo: GraphRepository = Depends(get_graph_repo),
):
    """Find contradictory claims about an entity."""
    try:
        resolved_key = await repo.resolve_entity_key(entity_key) or entity_key
        contradictions = await repo.find_contradictory_claims(resolved_key)
        return {"contradictions": [c.model_dump() for c in contradictions]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities/{entity_key}/claims")
async def get_entity_claims(
    entity_key: str,
    limit: int = 20,
    repo: GraphRepository = Depends(get_graph_repo),
):
    """Get claims about an entity."""
    try:
        resolved_key = await repo.resolve_entity_key(entity_key) or entity_key
        claims = await repo.get_claims_by_entity(resolved_key, limit=limit)
        return {"claims": claims}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities/{entity_key}/documents")
async def get_entity_documents(
    entity_key: str,
    limit: int = 10,
    repo: GraphRepository = Depends(get_graph_repo),
):
    """Get documents related to an entity."""
    try:
        resolved_key = await repo.resolve_entity_key(entity_key) or entity_key
        docs = await repo.get_related_documents(resolved_key, limit=limit)
        return {"documents": docs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gaps")
async def find_research_gaps(
    limit: int = 50,
    repo: GraphRepository = Depends(get_graph_repo),
):
    """Find underexplored connections between entities."""
    try:
        gaps = await repo.find_gaps(limit=limit)
        return {"gaps": gaps}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trending")
async def find_trending_concepts(
    days: int = 365,
    limit: int = 20,
    repo: GraphRepository = Depends(get_graph_repo),
):
    """Find trending concepts based on recent mentions."""
    try:
        trending = await repo.find_trending_concepts(days=days, limit=limit)
        return {"trending": trending}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/communities")
async def detect_communities(
    repo: GraphRepository = Depends(get_graph_repo),
):
    """Detect communities in the entity graph."""
    try:
        communities = await repo.detect_communities()
        return {"communities": communities}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hypotheses")
async def create_hypothesis(
    hypothesis: HypothesisPayload,
    repo: GraphRepository = Depends(get_graph_repo),
):
    """Store a hypothesis in the graph."""
    try:
        hyp_id = await repo.upsert_hypothesis(hypothesis)
        return {"id": hyp_id, "hypothesis": hypothesis.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gaps")
async def create_research_gap(
    gap: ResearchGapPayload,
    repo: GraphRepository = Depends(get_graph_repo),
):
    """Store a research gap in the graph."""
    try:
        gap_id = await repo.upsert_research_gap(gap)
        return {"id": gap_id, "gap": gap.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/entities")
async def create_entity(
    entity: EntityPayload,
    repo: GraphRepository = Depends(get_graph_repo),
):
    """Create or update an entity."""
    try:
        key = await repo.upsert_entity(entity)
        return {"key": key, "entity": entity.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/claims")
async def create_claim(
    claim: ClaimPayload,
    repo: GraphRepository = Depends(get_graph_repo),
):
    """Create or update a claim."""
    try:
        claim_id = await repo.upsert_claim(claim)
        return {"id": claim_id, "claim": claim.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
