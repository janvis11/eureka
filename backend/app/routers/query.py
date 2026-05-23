from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import logging

from app.models.database import get_db
from app.models.models import Query
from app.services.rag_engine import RAGEngine
from app.config import get_settings
from app.services.shared import get_gateway
from app.services.retrieval.structural_rag_engine import get_structural_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/queries", tags=["queries"])
_gateway = get_gateway()
rag_engine = RAGEngine(gateway=_gateway)
structural_engine = get_structural_engine(gateway=_gateway)
settings = get_settings()


class QueryRequest(BaseModel):
    document_id: Optional[int] = None
    question: str
    top_k: int = 5
    use_structural: bool = True   # Use PageIndex-style retrieval when available


class QueryResponse(BaseModel):
    answer: str
    sources: List[dict]
    confidence: float


@router.post("/ask")
async def ask_question(
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    """
    Ask a question about uploaded document(s).

    Uses structural RAG (PageIndex-inspired) when documents are structurally
    indexed, falls back to vector search (FAISS) otherwise.
    """
    try:
        # ----------------------------------------------------------------
        # Try Structural RAG first (PageIndex-inspired)
        # ----------------------------------------------------------------
        structural_stats = structural_engine.get_stats()
        has_structural_docs = structural_stats.get("indexed_documents", 0) > 0

        if request.use_structural and has_structural_docs:
            doc_ids = [str(request.document_id)] if request.document_id else None
            result = await structural_engine.answer(
                query=request.question,
                doc_ids=doc_ids,
            )

            if result.get("evidence"):
                # Format sources with breadcrumbs
                sources = [
                    {
                        "document_id": ev.get("document_id"),
                        "title": ev.get("document_title", ev.get("title", "Unknown")),
                        "section": ev.get("title"),
                        "breadcrumb": ev.get("breadcrumb"),
                        "text_preview": ev.get("text_preview", "")[:200],
                        "retrieval_method": "structural_rag",
                    }
                    for ev in result["evidence"]
                ]

                # Save to history
                query_record = None
                try:
                    query_record = Query(
                        query_text=request.question,
                        response=result.get("answer", ""),
                        sources=sources,
                        response_time=0.0
                    )
                    db.add(query_record)
                    db.commit()
                    db.refresh(query_record)
                except Exception:
                    db.rollback()

                return {
                    "query_id": query_record.id if query_record else None,
                    "answer": result.get("answer", ""),
                    "sources": sources,
                    "confidence": min(1.0, len(result["evidence"]) * 0.2),
                    "retrieved_chunks": len(result["evidence"]),
                    "retrieval_method": "structural_rag",
                    "reasoning_trace": result.get("reasoning_trace", ""),
                    "navigation_path": result.get("navigation_path", []),
                }

        # ----------------------------------------------------------------
        # Fallback: Vector-based semantic search
        # ----------------------------------------------------------------
        search_k = max(request.top_k, 50) if request.document_id else request.top_k
        results = await rag_engine.semantic_search(request.question, top_k=search_k)

        if not results:
            return {
                "answer": "I couldn't find relevant information in the uploaded documents. Please upload documents first or try a different question.",
                "sources": [],
                "confidence": 0.0,
                "retrieval_method": "none",
                "error": "NO_DOCUMENTS_FOUND"
            }

        if request.document_id:
            results = [
                r for r in results
                if r.get("metadata", {}).get("document_id") == str(request.document_id)
            ][:request.top_k]
            if not results:
                return {
                    "answer": f"No relevant information found in document {request.document_id}.",
                    "sources": [],
                    "confidence": 0.0,
                    "retrieval_method": "vector",
                }

        answer_result = await rag_engine.generate_answer(
            question=request.question,
            context=results
        )

        sources = []
        for result in results[:request.top_k]:
            sources.append({
                "document_id": result.get("metadata", {}).get("document_id"),
                "title": result.get("metadata", {}).get("document_title", "Unknown"),
                "chunk_index": result.get("metadata", {}).get("chunk_index"),
                "relevance_score": 1.0 - (result.get("distance", 0) / 100),
                "text_preview": result.get("text", "")[:200],
                "retrieval_method": "vector",
            })

        query_record = None
        try:
            query_record = Query(
                query_text=request.question,
                response=answer_result.get("answer", ""),
                sources=sources,
                response_time=0.0
            )
            db.add(query_record)
            db.commit()
            db.refresh(query_record)
        except Exception:
            db.rollback()

        return {
            "query_id": query_record.id if query_record else None,
            "answer": answer_result.get("answer", ""),
            "sources": sources,
            "confidence": answer_result.get("confidence", 0.0),
            "retrieved_chunks": len(results),
            "retrieval_method": "vector_faiss",
        }

    except Exception as e:
        logger.error(f"Query error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@router.post("/structural-ask")
async def structural_ask(
    request: QueryRequest,
):
    """
    PageIndex-style structural query — explicit endpoint.
    Always uses section-tree navigation, never falls back to vector.
    Returns full reasoning trace and navigation breadcrumbs.
    """
    try:
        doc_ids = [str(request.document_id)] if request.document_id else None
        result = await structural_engine.answer(
            query=request.question,
            doc_ids=doc_ids,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_query_history(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get query history."""
    queries = db.query(Query).order_by(Query.timestamp.desc()).offset(skip).limit(limit).all()

    return {
        "queries": [
            {
                "id": q.id,
                "query": q.query_text,
                "response": q.response,
                "sources": q.sources,
                "timestamp": q.timestamp.isoformat(),
                "response_time": q.response_time
            }
            for q in queries
        ],
        "total": db.query(Query).count()
    }
