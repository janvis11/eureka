"""Evidence pack builder for retrieval results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.services.retrieval.query_planner import QueryPlan


@dataclass
class EvidenceItem:
    """A single piece of evidence."""
    source_id: str
    chunk_id: Optional[str]
    text: str
    score: float
    retrieval_sources: List[str] = field(default_factory=list)
    graph_path: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    evidence_type: str = "supporting"  # supporting, counter, neutral


@dataclass
class EvidencePack:
    """Collection of evidence for a query."""
    query: str
    intent: str
    items: List[EvidenceItem] = field(default_factory=list)
    counter_evidence: List[EvidenceItem] = field(default_factory=list)
    graph_paths: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "intent": self.intent,
            "items": [
                {
                    "source_id": item.source_id,
                    "chunk_id": item.chunk_id,
                    "text": item.text,
                    "score": item.score,
                    "retrieval_sources": item.retrieval_sources,
                    "graph_path": item.graph_path,
                    "metadata": item.metadata,
                    "evidence_type": item.evidence_type,
                }
                for item in self.items
            ],
            "counter_evidence": [
                {
                    "source_id": item.source_id,
                    "chunk_id": item.chunk_id,
                    "text": item.text,
                    "score": item.score,
                    "retrieval_sources": item.retrieval_sources,
                    "evidence_type": "counter",
                }
                for item in self.counter_evidence
            ],
            "graph_paths": self.graph_paths,
            "metadata": self.metadata,
        }


async def build_evidence_pack(
    query: str,
    plan: QueryPlan,
    retrieval_results: List[Dict[str, Any]],
    graph_paths: Optional[List[Dict[str, Any]]] = None,
    counter_evidence: Optional[List[Dict[str, Any]]] = None,
) -> EvidencePack:
    """Build an evidence pack from retrieval results.

    Args:
        query: Original query
        plan: Query plan
        retrieval_results: Combined retrieval results
        graph_paths: Optional graph paths
        counter_evidence: Optional counter-evidence items

    Returns:
        EvidencePack with organized evidence
    """
    items = []
    counter_items = []

    for result in retrieval_results:
        item = EvidenceItem(
            source_id=result.get("doc_id", result.get("id", "unknown")),
            chunk_id=result.get("chunk_id"),
            text=result.get("text", ""),
            score=result.get("score", 0.0),
            retrieval_sources=result.get("retrieval_sources", []),
            graph_path=result.get("graph_path", []),
            metadata=result.get("metadata", {}),
            evidence_type="supporting",
        )
        items.append(item)

    # Process counter-evidence if provided
    if counter_evidence:
        for result in counter_evidence:
            item = EvidenceItem(
                source_id=result.get("doc_id", result.get("id", "unknown")),
                chunk_id=result.get("chunk_id"),
                text=result.get("text", ""),
                score=result.get("score", 0.0),
                retrieval_sources=result.get("retrieval_sources", []),
                evidence_type="counter",
            )
            counter_items.append(item)

    return EvidencePack(
        query=query,
        intent=plan.intent.value if hasattr(plan.intent, "value") else str(plan.intent),
        items=items,
        counter_evidence=counter_items,
        graph_paths=graph_paths or [],
        metadata={
            "total_items": len(items),
            "counter_items": len(counter_items),
            "graph_paths": len(graph_paths or []),
            "retrievers_used": plan.retrievers,
        },
    )


def format_evidence_for_prompt(evidence_pack: EvidencePack) -> str:
    """Format evidence pack for LLM prompt.

    Args:
        evidence_pack: Evidence pack to format

    Returns:
        Formatted string for prompt
    """
    lines = []
    lines.append(f"Query: {evidence_pack.query}")
    lines.append(f"Intent: {evidence_pack.intent}")
    lines.append("")

    if evidence_pack.items:
        lines.append("Evidence:")
        for i, item in enumerate(evidence_pack.items, 1):
            lines.append(f"[{i}] (score={item.score:.2f}, sources={','.join(item.retrieval_sources)})")
            lines.append(f"    {item.text[:200]}...")
        lines.append("")

    if evidence_pack.counter_evidence:
        lines.append("Counter-Evidence:")
        for i, item in enumerate(evidence_pack.counter_evidence, 1):
            lines.append(f"[{i}] (score={item.score:.2f})")
            lines.append(f"    {item.text[:200]}...")
        lines.append("")

    if evidence_pack.graph_paths:
        lines.append("Graph Paths:")
        for i, path in enumerate(evidence_pack.graph_paths, 1):
            nodes = path.get("nodes", [])
            node_names = [n.get("name", n.get("key", "?")) for n in nodes]
            lines.append(f"[{i}] {' -> '.join(node_names)}")

    return "\n".join(lines)
