"""Graph schema definitions for Neo4j."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class DocumentGraphPayload(BaseModel):
    """Document payload for graph upsert."""
    id: str
    title: str
    source_type: Literal["pdf", "web", "note", "patent", "dataset"]
    created_at: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChunkGraphPayload(BaseModel):
    """Chunk payload for graph upsert."""
    id: str
    document_id: str
    text: str
    chunk_index: int
    token_count: int
    source_span_start: Optional[int] = None
    source_span_end: Optional[int] = None


class EntityPayload(BaseModel):
    """Entity payload for graph upsert."""
    key: str
    name: str
    type: Literal[
        "METHOD", "DATASET", "CONCEPT", "METRIC", "ORGANIZATION",
        "PERSON", "MATERIAL", "GENE", "DISEASE", "TASK"
    ]
    aliases: List[str] = Field(default_factory=list)
    description: Optional[str] = None


class ClaimPayload(BaseModel):
    """Claim payload for graph upsert."""
    id: str
    text: str
    claim_type: Literal[
        "finding", "limitation", "method", "comparison",
        "definition", "future_work"
    ]
    polarity: Literal["positive", "negative", "neutral"]
    confidence: float = Field(ge=0.0, le=1.0)
    source_quote: str
    chunk_id: Optional[str] = None


class GraphNeighborhood(BaseModel):
    """Neighborhood of an entity in the graph."""
    center_key: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]


class GraphPath(BaseModel):
    """A path in the graph."""
    nodes: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    length: int


class ContradictionCandidate(BaseModel):
    """A pair of potentially contradictory claims."""
    entity_key: str
    claim_a_id: str
    claim_a_text: str
    claim_b_id: str
    claim_b_text: str
    contradiction_score: float


class HypothesisPayload(BaseModel):
    """Hypothesis payload for graph storage."""
    id: str
    text: str
    novelty_score: float
    feasibility_score: float
    falsifiability_score: float
    evidence_count: int
    supporting_claim_ids: List[str]
    counter_claim_ids: List[str]
    experiment_plan: Optional[str] = None


class ResearchGapPayload(BaseModel):
    """Research gap payload for graph storage."""
    id: str
    description: str
    entity_keys: List[str]
    evidence_count: int
    weakness_score: float
