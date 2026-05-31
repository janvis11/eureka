"""
Discovery Router — Neo4j-powered discovery engine endpoints.

Features:
- /analyze          Full LLM-based discovery pipeline
- /graph/gaps       Neo4j Cypher gap detection
- /graph/contradictions  Neo4j graph contradiction mining
- /graph/hypotheses LLM reasoning over graph paths
- /graph/bridges    Neo4j shortest-path bridge discovery
- /structural-query PageIndex-style structural search
- Plus all legacy endpoints kept for compatibility
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging
import uuid
import json
import re

from app.models.database import get_db
from app.models.models import Discovery, Document
from app.services.discovery.engine import DiscoveryEngine
from app.services.discovery.scoring import rank_hypotheses
from app.services.rag_engine import RAGEngine
from app.services.knowledge_graph import KeywordExtractor
from app.services.shared import get_gateway
from app.config import get_settings
from app.services.model_gateway.base import ChatMessage, GenerationRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/discovery", tags=["discovery"])
settings = get_settings()

# Initialize services
_gateway = get_gateway()
rag_engine = RAGEngine(gateway=_gateway)
keyword_extractor = KeywordExtractor(gateway=_gateway)

# New agent-based discovery engine
_discovery_engine: Optional[DiscoveryEngine] = None


def get_discovery_engine() -> DiscoveryEngine:
    global _discovery_engine
    if _discovery_engine is None:
        _discovery_engine = DiscoveryEngine()
    return _discovery_engine


# ---------------------------------------------------------------------------
# Helper: get Neo4j client (graceful if unavailable)
# ---------------------------------------------------------------------------

async def _get_graph_repo():
    """Get graph repository, returns None if Neo4j unavailable."""
    try:
        from app.services.graph.neo4j_client import get_neo4j_client
        from app.services.graph.repository import GraphRepository
        client = get_neo4j_client()
        if not client.is_connected:
            await client.connect()
        return GraphRepository(client)
    except Exception as e:
        logger.warning(f"Neo4j unavailable: {e}")
        return None


async def _generate(prompt: str, max_tokens: int = 800) -> str:
    """LLM generation helper."""
    try:
        result = await _gateway.generate(
            GenerationRequest(
                messages=[ChatMessage(role="user", content=prompt)],
                temperature=0.7,
                max_tokens=max_tokens,
            )
        )
        return result.text
    except Exception as e:
        logger.error(f"Generation error: {e}")
        return ""


def _parse_json(text: str) -> dict:
    """Extract JSON from LLM text."""
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return {}


def _parse_json_list(text: str) -> list:
    """Extract JSON array from LLM text."""
    try:
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return []


# ---------------------------------------------------------------------------
# Neo4j-Powered Discovery: Gap Detection
# ---------------------------------------------------------------------------

@router.get("/graph/gaps")
async def get_graph_gaps(
    limit: int = 15,
    db: Session = Depends(get_db),
):
    """
    Neo4j-powered research gap detection.

    Finds concepts that appear across multiple documents but have few
    connecting relationships — indicating unexplored connections.
    Falls back to LLM-only analysis if Neo4j unavailable.
    """
    graph_repo = await _get_graph_repo()

    # Try Neo4j gap detection first
    if graph_repo:
        try:
            raw_gaps = await graph_repo.find_gaps(limit=limit)
            if raw_gaps:
                gaps = []
                for i, gap in enumerate(raw_gaps[:limit]):
                    a_key = gap.get("a_key", "Unknown concept A")
                    b_key = gap.get("b_key", "Unknown concept B")
                    evidence = gap.get("evidence_count", 1)
                    strength = gap.get("strength", 0)

                    gaps.append({
                        "id": f"gap-graph-{i+1}",
                        "title": f"Unexplored link: {a_key} ↔ {b_key}",
                        "description": (
                            f"Concept '{a_key}' and '{b_key}' appear in {evidence} document(s) "
                            f"but have only {strength} explicit connection(s) in the knowledge graph. "
                            f"This gap may represent an important unexplored research direction."
                        ),
                        "type": "knowledge_graph_gap",
                        "impact": "high" if evidence > 3 else "medium",
                        "confidence": min(0.95, 0.5 + evidence * 0.08),
                        "entities": [a_key, b_key],
                        "source": "neo4j_graph",
                        "evidence_count": evidence,
                    })

                return {"gaps": gaps, "source": "neo4j", "count": len(gaps)}
        except Exception as e:
            logger.warning(f"Neo4j gap detection failed: {e}")

    # Fallback: LLM-based gap detection from documents
    documents = db.query(Document).filter(
        Document.processing_status == "completed"
    ).limit(5).all()

    if not documents:
        return {"gaps": [], "source": "none", "message": "No processed documents"}

    doc_texts = []
    for doc in documents:
        results = await rag_engine.semantic_search(f"research findings results", top_k=20)
        text = "\n".join([r.get("text", "") for r in results
                          if r.get("metadata", {}).get("document_id") == str(doc.id)][:10])
        if text:
            doc_texts.append(text)

    combined = "\n\n".join(doc_texts[:3])[:8000]
    prompt = f"""Analyze these research documents and identify research gaps — areas that need more investigation.

Documents:
{combined}

Output JSON with this exact structure:
{{
  "gaps": [
    {{
      "title": "Gap title",
      "description": "What is missing and why it matters",
      "type": "methodological|theoretical|empirical|application",
      "impact": "high|medium|low",
      "confidence": 0.75
    }}
  ]
}}"""

    response = await _generate(prompt, max_tokens=1200)
    parsed = _parse_json(response)
    gaps = parsed.get("gaps", [])

    normalized = [
        {
            "id": f"gap-llm-{i+1}",
            "title": g.get("title", f"Gap {i+1}"),
            "description": g.get("description", ""),
            "type": g.get("type", "methodological"),
            "impact": g.get("impact", "medium"),
            "confidence": float(g.get("confidence", 0.7)),
            "source": "llm",
        }
        for i, g in enumerate(gaps[:limit])
    ]

    return {"gaps": normalized, "source": "llm_fallback", "count": len(normalized)}


# ---------------------------------------------------------------------------
# Neo4j-Powered Discovery: Contradiction Mining
# ---------------------------------------------------------------------------

@router.get("/graph/contradictions")
async def get_graph_contradictions(
    entity: Optional[str] = None,
    limit: int = 10,
    db: Session = Depends(get_db),
):
    """
    Neo4j-powered contradiction detection.

    Finds claims with opposing polarity about the same entities.
    Uses LLM to score and explain each contradiction.
    Falls back to document-level LLM analysis if Neo4j unavailable.
    """
    contradictions = []
    graph_repo = await _get_graph_repo()

    # Neo4j-based contradiction finding
    if graph_repo:
        try:
            # Get all entities or specific entity
            if entity:
                resolved = await graph_repo.resolve_entity_key(entity) or entity
                entity_keys = [resolved]
            else:
                # Get most mentioned entities
                trending = await graph_repo.find_trending_concepts(days=3650, limit=10)
                entity_keys = [t.get("entity_key", "") for t in trending if t.get("entity_key")]

            for key in entity_keys[:5]:
                candidates = await graph_repo.find_contradictory_claims(key)
                for c in candidates[:3]:
                    # LLM-score the contradiction
                    score_prompt = f"""Do these two research claims contradict each other?

Claim A: {c.claim_a_text}
Claim B: {c.claim_b_text}

Respond with JSON:
{{
  "contradicts": true/false,
  "explanation": "Why they contradict",
  "severity": "high|medium|low",
  "resolution": "How this could be resolved"
}}"""
                    scored = _parse_json(await _generate(score_prompt, max_tokens=300))

                    if scored.get("contradicts", True):
                        contradictions.append({
                            "id": f"contra-{c.claim_a_id[:8]}-{c.claim_b_id[:8]}",
                            "entity": key,
                            "title": f"Contradiction about '{key}'",
                            "claim_a": c.claim_a_text,
                            "claim_b": c.claim_b_text,
                            "explanation": scored.get("explanation", "Opposing polarity detected"),
                            "severity": scored.get("severity", "medium"),
                            "resolution_hint": scored.get("resolution", ""),
                            "score": float(c.contradiction_score),
                            "source": "neo4j_llm",
                        })

            if contradictions:
                return {
                    "contradictions": contradictions[:limit],
                    "source": "neo4j",
                    "count": len(contradictions)
                }
        except Exception as e:
            logger.warning(f"Neo4j contradiction detection failed: {e}")

    # Fallback: document-pair LLM analysis
    documents = db.query(Document).filter(
        Document.processing_status == "completed"
    ).limit(4).all()

    if len(documents) < 2:
        return {"contradictions": [], "source": "none", "message": "Need at least 2 documents"}

    doc_texts = []
    for doc in documents:
        results = await rag_engine.semantic_search("key findings results conclusions", top_k=10)
        text = "\n".join([r.get("text", "") for r in results
                          if r.get("metadata", {}).get("document_id") == str(doc.id)][:5])
        if text:
            doc_texts.append({"id": doc.id, "title": doc.title, "text": text[:2000]})

    for i in range(min(len(doc_texts), 3)):
        for j in range(i + 1, min(len(doc_texts), 3)):
            prompt = f"""Compare these two research excerpts and identify contradictions.

Document 1 ({doc_texts[i]['title']}):
{doc_texts[i]['text']}

Document 2 ({doc_texts[j]['title']}):
{doc_texts[j]['text']}

Output JSON:
{{
  "has_contradiction": true/false,
  "title": "Brief contradiction title",
  "claim_a": "Quote or paraphrase from doc 1",
  "claim_b": "Quote or paraphrase from doc 2",
  "explanation": "How they contradict",
  "severity": "high|medium|low",
  "confidence": 0.0-1.0
}}"""
            parsed = _parse_json(await _generate(prompt, max_tokens=500))
            if parsed.get("has_contradiction"):
                contradictions.append({
                    "id": f"contra-docs-{i}-{j}",
                    "entity": "cross-document",
                    "title": parsed.get("title", "Contradiction detected"),
                    "claim_a": parsed.get("claim_a", ""),
                    "claim_b": parsed.get("claim_b", ""),
                    "explanation": parsed.get("explanation", ""),
                    "severity": parsed.get("severity", "medium"),
                    "resolution_hint": "",
                    "score": float(parsed.get("confidence", 0.7)),
                    "source": "llm_fallback",
                    "doc_a": doc_texts[i]["title"],
                    "doc_b": doc_texts[j]["title"],
                })

    return {"contradictions": contradictions[:limit], "source": "llm_fallback", "count": len(contradictions)}


# ---------------------------------------------------------------------------
# Neo4j-Powered Discovery: Hypothesis Generation
# ---------------------------------------------------------------------------

@router.post("/graph/hypotheses")
async def generate_graph_hypotheses(
    db: Session = Depends(get_db),
):
    """
    Generate hypotheses by reasoning over the knowledge graph.

    Uses Neo4j paths between concepts as evidence, then LLM generates
    testable hypotheses from those graph-based connections.
    """
    hypotheses = []
    graph_repo = await _get_graph_repo()

    # Get context from knowledge graph
    graph_context = ""
    if graph_repo:
        try:
            trending = await graph_repo.find_trending_concepts(days=3650, limit=20)
            if trending:
                concepts = [t.get("entity_name", t.get("entity_key", "")) for t in trending[:10]]
                graph_context = f"Key concepts from knowledge graph: {', '.join(concepts)}\n\n"

                # Get gaps to base hypotheses on
                gaps_data = await graph_repo.find_gaps(limit=10)
                if gaps_data:
                    gap_pairs = [(g.get("a_key", ""), g.get("b_key", "")) for g in gaps_data[:5]]
                    graph_context += "Unexplored connections (research gaps):\n"
                    for a, b in gap_pairs:
                        graph_context += f"  • {a} ↔ {b}\n"
        except Exception as e:
            logger.warning(f"Graph context retrieval failed: {e}")

    # Also get document context
    documents = db.query(Document).filter(
        Document.processing_status == "completed"
    ).limit(3).all()

    doc_context = ""
    for doc in documents:
        results = await rag_engine.semantic_search("methods findings conclusions", top_k=10)
        text = "\n".join([r.get("text", "") for r in results[:5]])
        if text:
            doc_context += f"\n\n[{doc.title}]:\n{text[:1500]}"

    prompt = f"""You are a research scientist generating novel, testable hypotheses.

{graph_context}

Document Evidence:
{doc_context[:5000]}

Generate 5 novel research hypotheses. Each must be:
1. Specific and testable
2. Based on the evidence above
3. Novel — not already established
4. Falsifiable
5. Honest about evidence and counter-evidence

Output JSON array:
[
  {{
    "hypothesis": "Specific testable statement",
    "rationale": "Why this is plausible based on evidence",
    "evidence": ["supporting evidence item"],
    "counter_evidence": ["weakness, contradiction, or missing evidence"],
    "methodology": "How to test this",
    "validation_plan": "Concrete validation plan",
    "expected_impact": "What finding this would mean for the field",
    "novelty": "What makes this new",
    "feasibility": "Why this can be tested with realistic data/methods",
    "falsifiability": "What result would disprove it",
    "novelty_score": 0.0-1.0,
    "feasibility_score": 0.0-1.0,
    "falsifiability_score": 0.0-1.0,
    "confidence": 0.0-1.0,
    "evidence_sources": ["concept1", "concept2"]
  }}
]

JSON array only:"""

    response = await _generate(prompt, max_tokens=2000)
    parsed_list = _parse_json_list(response)

    for i, h in enumerate(parsed_list[:8]):
        novelty_score = float(h.get("novelty_score", h.get("confidence", 0.65)))
        feasibility_score = float(h.get("feasibility_score", 0.7))
        falsifiability_score = float(h.get("falsifiability_score", 0.8))
        hypotheses.append({
            "id": f"hyp-graph-{uuid.uuid4().hex[:8]}",
            "text": h.get("hypothesis", ""),
            "rationale": h.get("rationale", ""),
            "evidence": h.get("evidence", h.get("evidence_sources", [])),
            "counter_evidence": h.get("counter_evidence", []),
            "methodology": h.get("methodology", ""),
            "validation_plan": h.get("validation_plan", h.get("methodology", "")),
            "expected_impact": h.get("expected_impact", ""),
            "novelty": h.get("novelty", ""),
            "feasibility": h.get("feasibility", ""),
            "falsifiability": h.get("falsifiability", ""),
            "novelty_score": novelty_score,
            "feasibility_score": feasibility_score,
            "falsifiability_score": falsifiability_score,
            "confidence": float(h.get("confidence", (novelty_score + feasibility_score + falsifiability_score) / 3)),
            "evidence_sources": h.get("evidence_sources", []),
            "source": "neo4j_graph" if graph_context else "llm_only",
            "status": "proposed",
            "votes_up": 0,
            "votes_down": 0,
        })

    # Persist to Neo4j if available
    if graph_repo and hypotheses:
        try:
            from app.services.graph.schema import HypothesisPayload
            for hyp in hypotheses[:3]:
                await graph_repo.upsert_hypothesis(HypothesisPayload(
                    id=hyp["id"],
                    text=hyp["text"],
                    novelty_score=hyp["novelty_score"],
                    feasibility_score=hyp["feasibility_score"],
                    falsifiability_score=hyp["falsifiability_score"],
                    evidence_count=len(hyp.get("evidence_sources", [])) + len(hyp.get("evidence", [])),
                    supporting_claim_ids=[],
                    counter_claim_ids=[],
                    experiment_plan=hyp.get("validation_plan") or hyp.get("methodology", ""),
                ))
        except Exception as e:
            logger.warning(f"Hypothesis persistence to Neo4j failed: {e}")

    return {
        "hypotheses": hypotheses,
        "count": len(hypotheses),
        "source": "neo4j_graph" if graph_context else "llm_document",
    }


# ---------------------------------------------------------------------------
# Structural Query (PageIndex-style)
# ---------------------------------------------------------------------------

class StructuralQueryRequest(BaseModel):
    query: str
    document_ids: Optional[List[int]] = None


@router.post("/structural-query")
async def structural_query(request: StructuralQueryRequest):
    """
    PageIndex-style structural retrieval.
    LLM navigates document section trees to find precise answers.
    """
    from app.services.retrieval.structural_rag_engine import get_structural_engine
    engine = get_structural_engine(gateway=_gateway)

    doc_ids = [str(d) for d in request.document_ids] if request.document_ids else None
    result = await engine.answer(query=request.query, doc_ids=doc_ids)
    return result


# ---------------------------------------------------------------------------
# Main discovery analysis (full pipeline)
# ---------------------------------------------------------------------------

@router.post("/analyze")
async def analyze_documents(db: Session = Depends(get_db)):
    """Run full discovery analysis on all uploaded documents."""
    try:
        documents = db.query(Document).filter(
            Document.processing_status == "completed"
        ).all()

        if not documents:
            raise HTTPException(status_code=400, detail="No processed documents found")

        # Get document texts
        documents_texts = []
        for doc in documents:
            search_query = f"document {doc.id} {doc.title if doc.title else ''}"
            results = await rag_engine.semantic_search(search_query, top_k=50)
            doc_chunks = [
                r.get("text", "")
                for r in results
                if r.get("metadata", {}).get("document_id") == str(doc.id)
            ]
            if doc_chunks:
                documents_texts.append("\n\n".join(doc_chunks))
            elif results:
                documents_texts.append("\n\n".join([r.get("text", "") for r in results[:20]]))

        # Run the discovery engine
        from app.services.discovery_engine import DiscoveryEngine as LegacyDiscoveryEngine
        legacy_engine = LegacyDiscoveryEngine(rag_engine, keyword_extractor, gateway=_gateway)
        analysis = await legacy_engine.run_full_discovery(documents_texts)

        # Save to DB
        discovery = Discovery(
            analysis_type="full",
            gaps=analysis.get("gaps", []),
            hypotheses=analysis.get("hypotheses", []),
            contradictions=analysis.get("contradictions", []),
            trends=analysis.get("trends", []),
            doc_metadata=analysis.get("summary", {})
        )
        db.add(discovery)
        db.commit()
        db.refresh(discovery)

        return {"discovery_id": discovery.id, "analysis": analysis}

    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Existing endpoints (kept for frontend compatibility)
# ---------------------------------------------------------------------------

@router.get("/gaps")
async def get_research_gaps(db: Session = Depends(get_db)):
    """Get identified research gaps from last analysis."""
    discovery = db.query(Discovery).filter(
        Discovery.analysis_type == "full"
    ).order_by(Discovery.created_at.desc()).first()
    if not discovery:
        return {"gaps": []}
    return {"gaps": discovery.gaps}


@router.get("/hypotheses")
async def get_hypotheses(db: Session = Depends(get_db)):
    """Get generated hypotheses from last analysis."""
    discovery = db.query(Discovery).filter(
        Discovery.analysis_type == "full"
    ).order_by(Discovery.created_at.desc()).first()
    if not discovery:
        return {"hypotheses": []}
    return {"hypotheses": discovery.hypotheses}


@router.get("/contradictions")
async def get_contradictions(db: Session = Depends(get_db)):
    """Get detected contradictions from last analysis."""
    discovery = db.query(Discovery).filter(
        Discovery.analysis_type == "full"
    ).order_by(Discovery.created_at.desc()).first()
    if not discovery:
        return {"contradictions": []}
    return {"contradictions": discovery.contradictions}


@router.get("/trends")
async def get_trends(db: Session = Depends(get_db)):
    """Get detected trends from last analysis."""
    discovery = db.query(Discovery).filter(
        Discovery.analysis_type == "full"
    ).order_by(Discovery.created_at.desc()).first()
    if discovery and discovery.trends:
        return {"trends": discovery.trends, "source": "last_discovery"}

    graph_repo = await _get_graph_repo()
    if graph_repo:
        try:
            trending = await graph_repo.find_trending_concepts(days=settings.TREND_WINDOW_DAYS, limit=20)
            trends = [
                {
                    "id": item.get("entity_key"),
                    "title": item.get("entity_name") or item.get("entity_key"),
                    "entity_key": item.get("entity_key"),
                    "entity_name": item.get("entity_name"),
                    "description": (
                        f"{item.get('entity_name') or item.get('entity_key')} appears across "
                        f"{item.get('document_count', 0)} processed paper(s) and "
                        f"{item.get('mention_count', 0)} source chunk(s)."
                    ),
                    "velocity": "Rising" if item.get("document_count", 0) >= 3 else "Emerging",
                    "trend_score": min(1.0, 0.25 + item.get("mention_count", 0) * 0.08),
                    "document_count": item.get("document_count", 0),
                    "mention_count": item.get("mention_count", 0),
                }
                for item in trending
            ]
            return {"trends": trends, "source": "neo4j", "count": len(trends)}
        except Exception as e:
            logger.warning(f"Graph trend retrieval failed: {e}")

    return {"trends": [], "source": "none"}


@router.get("/summary")
async def get_discovery_summary(db: Session = Depends(get_db)):
    """Get summary of discovery analysis."""
    discovery = db.query(Discovery).filter(
        Discovery.analysis_type == "full"
    ).order_by(Discovery.created_at.desc()).first()

    if not discovery:
        return {
            "gaps_found": 0,
            "hypotheses_generated": 0,
            "contradictions_detected": 0,
            "trends_identified": 0,
        }
    return discovery.doc_metadata


@router.get("/graph-stats")
async def get_graph_stats(db: Session = Depends(get_db)):
    """Get knowledge graph statistics."""
    try:
        graph_repo = await _get_graph_repo()
        if graph_repo:
            stats = await graph_repo.get_stats()
            node_count = stats.get("entities", 0) + stats.get("documents", 0) + stats.get("claims", 0)
            relationship_count = stats.get("relationships", 0)
            trending = []
            if stats.get("entities", 0) and relationship_count:
                trending = await graph_repo.find_trending_concepts(days=3650, limit=10)
            return {
                "nodes": node_count,
                "edges": relationship_count,
                "density": 0.001 * relationship_count,
                "communities": max(1, stats.get("documents", 0) // 3) if node_count else 0,
                "breakdown": {
                    "papers": stats.get("documents", 0),
                    "concepts": stats.get("entities", 0),
                    "claims": stats.get("claims", 0),
                    "hypotheses": stats.get("hypotheses", 0),
                },
                "top_entities": [
                    item.get("entity_name") or item.get("entity_key")
                    for item in trending
                    if item.get("entity_name") or item.get("entity_key")
                ],
                "source": "neo4j",
            }
    except Exception as e:
        logger.warning(f"Graph stats from Neo4j failed: {e}")

    doc_count = db.query(Document).filter(Document.processing_status == "completed").count()
    return {
        "nodes": doc_count,
        "edges": 0,
        "density": 0.0,
        "communities": 0,
        "breakdown": {"papers": doc_count, "concepts": 0, "claims": 0, "hypotheses": 0},
        "top_entities": [],
        "source": "documents_only",
    }


class PathRequest(BaseModel):
    concept1: str
    concept2: str
    max_depth: int = 4


@router.post("/path")
async def find_path(request: PathRequest, db: Session = Depends(get_db)):
    """Find path between two concepts in knowledge graph."""
    graph_repo = await _get_graph_repo()
    if graph_repo:
        try:
            source_key = await graph_repo.resolve_entity_key(request.concept1) or request.concept1
            target_key = await graph_repo.resolve_entity_key(request.concept2) or request.concept2
            paths = await graph_repo.find_bridge_paths(
                source_key=source_key,
                target_key=target_key,
                max_hops=request.max_depth,
            )
            if paths:
                formatted = []
                for p in paths[:3]:
                    node_names = [n.get("name", n.get("key", "?")) for n in p.nodes]
                    formatted.append({"nodes": node_names, "length": p.length})
                return {"paths": formatted, "concept1": request.concept1, "concept2": request.concept2}
        except Exception as e:
            logger.warning(f"Neo4j path search failed: {e}")

    # Fallback: vector-based
    results1 = await rag_engine.semantic_search(request.concept1, top_k=10)
    results2 = await rag_engine.semantic_search(request.concept2, top_k=10)
    doc_ids1 = set(r.get("metadata", {}).get("document_id") for r in results1)
    doc_ids2 = set(r.get("metadata", {}).get("document_id") for r in results2)
    common = doc_ids1 & doc_ids2

    if common:
        return {
            "paths": [{"nodes": [request.concept1, "shared_research", request.concept2], "length": 2}],
            "concept1": request.concept1,
            "concept2": request.concept2,
        }
    return {"paths": [], "message": f"No path found between {request.concept1} and {request.concept2}"}


class VoteRequest(BaseModel):
    direction: str


@router.post("/hypotheses/{hypothesis_id}/vote")
async def vote_on_hypothesis(
    hypothesis_id: str,
    vote: VoteRequest,
    db: Session = Depends(get_db)
):
    """Vote on a hypothesis."""
    direction = vote.direction.lower()
    if direction not in {"up", "down"}:
        raise HTTPException(status_code=400, detail="Use 'up' or 'down'")

    discovery = db.query(Discovery).filter(
        Discovery.analysis_type == "full"
    ).order_by(Discovery.created_at.desc()).first()

    if discovery and discovery.hypotheses:
        hypotheses = list(discovery.hypotheses)
        hypothesis = None
        for idx, hyp in enumerate(hypotheses):
            if str(hyp.get("id", idx)) == str(hypothesis_id):
                hypothesis = hyp
                break

        if hypothesis:
            if direction == "up":
                hypothesis["votes_up"] = hypothesis.get("votes_up", 0) + 1
            else:
                hypothesis["votes_down"] = hypothesis.get("votes_down", 0) + 1

            discovery.hypotheses = hypotheses
            db.commit()

            return {
                "id": hypothesis_id,
                "votes_up": hypothesis.get("votes_up", 0),
                "votes_down": hypothesis.get("votes_down", 0),
                "source": "discovery_table",
            }

    graph_repo = await _get_graph_repo()
    if graph_repo:
        try:
            votes = await graph_repo.vote_hypothesis(hypothesis_id, direction)
            if votes:
                return {
                    "id": hypothesis_id,
                    **votes,
                    "source": "neo4j_graph",
                }
        except Exception as e:
            logger.warning(f"Graph hypothesis vote failed: {e}")

    raise HTTPException(status_code=404, detail="Hypothesis not found")


# New agent-based endpoints (kept for compatibility)

class DiscoveryQuery(BaseModel):
    query: str
    top_k: int = 15
    generate_hypotheses: bool = True


@router.post("/run")
async def run_discovery(
    request: DiscoveryQuery,
    engine: DiscoveryEngine = Depends(get_discovery_engine),
):
    """Run agent-based discovery pipeline."""
    try:
        report = await engine.run_full_discovery(
            query=request.query,
            top_k=request.top_k,
            generate_hypotheses=request.generate_hypotheses,
        )
        return report
    except Exception as e:
        logger.error(f"Discovery failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ExperimentDesignRequest(BaseModel):
    hypothesis: str
    why_it_matters: str = ""
    supporting_evidence: List[str] = []


@router.post("/experiments/design")
async def design_experiment(
    request: ExperimentDesignRequest,
    engine: DiscoveryEngine = Depends(get_discovery_engine),
):
    """Design an experiment to validate a hypothesis."""
    try:
        design = await engine.experiment_designer.design(
            hypothesis=request.hypothesis,
            why_it_matters=request.why_it_matters,
            supporting_evidence=request.supporting_evidence,
        )
        return design
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bridges")
async def find_bridge_paths(
    source: str,
    target: str,
    max_hops: int = 4,
    engine: DiscoveryEngine = Depends(get_discovery_engine),
):
    """Find bridge paths between two entities."""
    try:
        bridges = await engine.bridge_finder.find_bridges(
            source_entities=[source],
            target_entities=[target],
            max_hops=max_hops,
        )
        return {"bridges": bridges}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
