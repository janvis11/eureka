from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from app.models.database import get_db
from app.models.models import Query
from app.services.rag_engine import RAGEngine
from app.config import get_settings
from app.services.shared import hf_client as shared_hf_client

router = APIRouter(prefix="/queries", tags=["queries"])
rag_engine = RAGEngine(hf_client=shared_hf_client)
settings = get_settings()


class QueryRequest(BaseModel):
    document_id: Optional[int] = None  # Optional: query all documents if None
    question: str
    top_k: int = 5


class QueryResponse(BaseModel):
    answer: str
    sources: List[dict]
    confidence: float


@router.post("/ask")
async def ask_question(
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    """Ask a question about uploaded document(s) using RAG."""
    try:
        # Perform semantic search
        results = await rag_engine.semantic_search(request.question, top_k=request.top_k)
        
        if not results:
            return {
                "answer": "I couldn't find relevant information in the uploaded documents. Please upload documents first or try a different question.",
                "sources": [],
                "confidence": 0.0
            }
        
        # Filter by document_id if specified
        if request.document_id:
            results = [
                r for r in results 
                if r.get("metadata", {}).get("document_id") == str(request.document_id)
            ]
            if not results:
                return {
                    "answer": f"No relevant information found in document {request.document_id}.",
                    "sources": [],
                    "confidence": 0.0
                }
        
        # Generate answer using LLM
        answer_result = await rag_engine.generate_answer(
            question=request.question,
            context=results
        )
        
        # Format sources
        sources = []
        for i, result in enumerate(results[:request.top_k]):
            sources.append({
                "document_id": result.get("metadata", {}).get("document_id"),
                "title": result.get("metadata", {}).get("document_title", "Unknown"),
                "chunk_index": result.get("metadata", {}).get("chunk_index"),
                "relevance_score": 1.0 - (result.get("distance", 0) / 100),  # Normalize distance
                "text_preview": result.get("text", "")[:200] + "..." if len(result.get("text", "")) > 200 else result.get("text", "")
            })
        
        # Save query to database
        query_record = Query(
            query_text=request.question,
            response=answer_result.get("answer", ""),
            sources=sources,
            response_time=0.0  # Could track this if needed
        )
        db.add(query_record)
        db.commit()
        db.refresh(query_record)
        
        return {
            "query_id": query_record.id,
            "answer": answer_result.get("answer", ""),
            "sources": sources,
            "confidence": answer_result.get("confidence", 0.0),
            "retrieved_chunks": len(results)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


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
