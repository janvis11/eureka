from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from app.models.database import get_db
from app.models.models import Discovery, Document
from app.services.discovery_engine import DiscoveryEngine
from app.services.rag_engine import RAGEngine
from app.services.knowledge_graph import KeywordExtractor
from app.services.shared import hf_client as shared_hf_client
from app.config import get_settings

router = APIRouter(prefix="/discovery", tags=["discovery"])
settings = get_settings()

# Initialize services
rag_engine = RAGEngine(hf_client=shared_hf_client)
keyword_extractor = KeywordExtractor(hf_client=shared_hf_client)
discovery_engine = DiscoveryEngine(rag_engine, keyword_extractor, hf_client=shared_hf_client)


@router.post("/analyze")
async def analyze_documents(
    db: Session = Depends(get_db)
):
    """Run discovery analysis on all uploaded documents."""
    try:
        # Get all documents
        documents = db.query(Document).filter(
            Document.processing_status == "completed"
        ).all()
        
        if not documents:
            raise HTTPException(status_code=400, detail="No processed documents found")
        
        # Get document texts from vector store by document ID
        documents_texts = []
        for doc in documents:
            # Search for chunks specific to this document
            # Use document title or ID in search to get relevant chunks
            search_query = f"document {doc.id} {doc.title if doc.title else ''}"
            results = await rag_engine.semantic_search(search_query, top_k=50)
            
            # Filter results to this document's chunks
            doc_chunks = [
                r.get("text", "") 
                for r in results 
                if r.get("metadata", {}).get("document_id") == str(doc.id)
            ]
            
            if doc_chunks:
                doc_text = "\n\n".join(doc_chunks)
                documents_texts.append(doc_text)
            elif results:
                # Fallback: use all results if filtering fails
                doc_text = "\n\n".join([r.get("text", "") for r in results[:20]])
                documents_texts.append(doc_text)
        
        # Run discovery
        analysis = await discovery_engine.run_full_discovery(documents_texts)
        
        # Save discovery results
        discovery = Discovery(
            analysis_type="full",
            gaps=analysis.get("gaps", []),
            hypotheses=analysis.get("hypotheses", []),
            contradictions=analysis.get("contradictions", []),
            trends=analysis.get("trends", []),
            metadata=analysis.get("summary", {})
        )
        db.add(discovery)
        db.commit()
        db.refresh(discovery)
        
        return {
            "discovery_id": discovery.id,
            "analysis": analysis
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gaps")
async def get_research_gaps(
    db: Session = Depends(get_db)
):
    """Get identified research gaps."""
    discovery = db.query(Discovery).filter(
        Discovery.analysis_type == "full"
    ).order_by(Discovery.created_at.desc()).first()
    
    if not discovery:
        return {"gaps": []}
    
    return {"gaps": discovery.gaps}


@router.get("/hypotheses")
async def get_hypotheses(
    db: Session = Depends(get_db)
):
    """Get generated hypotheses."""
    discovery = db.query(Discovery).filter(
        Discovery.analysis_type == "full"
    ).order_by(Discovery.created_at.desc()).first()
    
    if not discovery:
        return {"hypotheses": []}
    
    return {"hypotheses": discovery.hypotheses}


@router.get("/trends")
async def get_trends(
    db: Session = Depends(get_db)
):
    """Get detected trends."""
    discovery = db.query(Discovery).filter(
        Discovery.analysis_type == "full"
    ).order_by(Discovery.created_at.desc()).first()
    
    if not discovery:
        return {"trends": []}
    
    return {"trends": discovery.trends}


@router.get("/keywords")
async def get_keywords(
    document_id: int = None,
    db: Session = Depends(get_db)
):
    """Get document keywords for knowledge graph visualization."""
    if document_id:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get document text from ChromaDB
        results = await rag_engine.semantic_search(f"document", top_k=50)
        doc_text = "\n".join([r.get("text", "") for r in results])
    else:
        # Get all documents
        documents = db.query(Document).filter(
            Document.processing_status == "completed"
        ).all()
        
        all_results = []
        for doc in documents:
            results = await rag_engine.semantic_search(f"document", top_k=20)
            all_results.extend(results)
        
        doc_text = "\n".join([r.get("text", "") for r in all_results])
    
    # Extract keywords
    keywords = keyword_extractor.extract_keywords(doc_text, num_keywords=30)
    phrases = keyword_extractor.extract_keyphrases(doc_text, num_phrases=20)
    
    return {
        "keywords": keywords,
        "phrases": phrases,
        "total": len(keywords) + len(phrases)
    }


@router.get("/contradictions")
async def get_contradictions(
    db: Session = Depends(get_db)
):
    """Get detected contradictions."""
    discovery = db.query(Discovery).filter(
        Discovery.analysis_type == "full"
    ).order_by(Discovery.created_at.desc()).first()
    
    if not discovery:
        return {"contradictions": []}
    
    return {"contradictions": discovery.contradictions}


@router.get("/graph-stats")
async def get_graph_stats(db: Session = Depends(get_db)):
    """Get knowledge graph statistics for visualization."""
    try:
        # Get basic stats from documents
        doc_count = db.query(Document).filter(Document.processing_status == "completed").count()
        
        # Get keywords/phrases for top entities
        top_entities = []
        keywords_count = 0
        phrases_count = 0
        
        if doc_count > 0:
            try:
                keywords_result = await get_keywords(None, db)
                top_entities = keywords_result.get("phrases", [])[:8]
                keywords_count = len(keywords_result.get("keywords", []))
                phrases_count = len(keywords_result.get("phrases", []))
            except Exception as e:
                logger.warning(f"Error getting keywords: {e}")
                top_entities = []
        
        # Calculate basic graph metrics
        total_nodes = doc_count * 10  # Estimate: ~10 concepts per document
        total_edges = total_nodes * 2  # Estimate: ~2 relationships per node
        
        return {
            "nodes": total_nodes,
            "edges": total_edges,
            "density": round(total_edges / (total_nodes * (total_nodes - 1)) if total_nodes > 1 else 0, 6),
            "communities": max(1, doc_count // 5),  # Estimate communities
            "top_entities": top_entities,
            "breakdown": {
                "papers": doc_count,
                "concepts": keywords_count,
                "methods": phrases_count
            }
        }
    except Exception as e:
        # Return default stats if error
        return {
            "nodes": 0,
            "edges": 0,
            "density": 0.0,
            "communities": 0,
            "top_entities": [],
            "breakdown": {
                "papers": 0,
                "concepts": 0,
                "methods": 0
            }
        }


class PathRequest(BaseModel):
    concept1: str
    concept2: str
    max_depth: int = 4


@router.post("/path")
async def find_path(
    request: PathRequest,
    db: Session = Depends(get_db)
):
    """Find path between two concepts in knowledge graph."""
    try:
        concept1 = request.concept1
        concept2 = request.concept2
        max_depth = request.max_depth
        
        if not concept1 or not concept2:
            return {"paths": [], "message": "Both concept1 and concept2 are required"}
        
        documents = db.query(Document).filter(Document.processing_status == "completed").all()
        
        if not documents:
            return {"paths": [], "message": "No documents available"}
        
        # Search for both concepts
        results1 = await rag_engine.semantic_search(concept1, top_k=10)
        results2 = await rag_engine.semantic_search(concept2, top_k=10)
        
        # Check if concepts appear in same documents
        doc_ids1 = set([r.get("metadata", {}).get("document_id") for r in results1])
        doc_ids2 = set([r.get("metadata", {}).get("document_id") for r in results2])
        
        common_docs = doc_ids1 & doc_ids2
        
        if common_docs:
            # Create a simple path through common documents
            path = [concept1, "related_research", concept2]
            return {
                "paths": [{"nodes": path, "length": len(path) - 1}],
                "concept1": concept1,
                "concept2": concept2
            }
        else:
            return {
                "paths": [],
                "message": f"No path found between {concept1} and {concept2}"
            }
    except Exception as e:
        return {
            "paths": [],
            "message": f"Error finding path: {str(e)}"
        }


class VoteRequest(BaseModel):
    direction: str


@router.post("/hypotheses/{hypothesis_id}/vote")
async def vote_on_hypothesis(
    hypothesis_id: str,
    vote: VoteRequest,
    db: Session = Depends(get_db)
):
    """Vote on a hypothesis."""
    try:
        # Get latest discovery
        discovery = db.query(Discovery).filter(
            Discovery.analysis_type == "full"
        ).order_by(Discovery.created_at.desc()).first()
        
        if not discovery or not discovery.hypotheses:
            raise HTTPException(status_code=404, detail="No hypotheses found")
        
        # Find hypothesis by ID (hypothesis_id is string from frontend)
        hypotheses = discovery.hypotheses
        hypothesis = None
        hypothesis_index = -1
        
        for idx, hyp in enumerate(hypotheses):
            # Check if ID matches (could be string or number)
            hyp_id = str(hyp.get("id", idx))
            if hyp_id == str(hypothesis_id):
                hypothesis = hyp
                hypothesis_index = idx
                break
        
        if not hypothesis:
            raise HTTPException(status_code=404, detail="Hypothesis not found")
        
        # Update votes
        direction = vote.direction.lower()
        if direction == "up":
            hypothesis["votes_up"] = hypothesis.get("votes_up", 0) + 1
        elif direction == "down":
            hypothesis["votes_down"] = hypothesis.get("votes_down", 0) + 1
        else:
            raise HTTPException(status_code=400, detail="Invalid vote direction. Use 'up' or 'down'")
        
        # Update discovery record
        discovery.hypotheses = hypotheses
        db.commit()
        
        return {
            "id": hypothesis_id,
            "votes_up": hypothesis.get("votes_up", 0),
            "votes_down": hypothesis.get("votes_down", 0)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_discovery_summary(
    db: Session = Depends(get_db)
):
    """Get summary of discovery analysis."""
    discovery = db.query(Discovery).filter(
        Discovery.analysis_type == "full"
    ).order_by(Discovery.created_at.desc()).first()
    
    if not discovery:
        return {
            "gaps_found": 0,
            "hypotheses_generated": 0,
            "contradictions_detected": 0,
            "trends_identified": 0
        }
    
    return discovery.metadata
