from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
from datetime import datetime

from app.models.database import get_db
from app.models.models import Document
from app.services.document_processor import DocumentProcessor
from app.services.rag_engine import RAGEngine
from app.services.knowledge_graph import KeywordExtractor
from app.services.shared import hf_client as shared_hf_client
from app.config import get_settings

router = APIRouter()
settings = get_settings()

# Initialize services
doc_processor = DocumentProcessor(
    chunk_size=settings.CHUNK_SIZE,
    chunk_overlap=settings.CHUNK_OVERLAP
)
rag_engine = RAGEngine(hf_client=shared_hf_client)
# Shared HF client for lightweight local tasks
keyword_extractor = KeywordExtractor(hf_client=shared_hf_client)


async def process_document_background(document_id: int, file_path: str, db: Session):
    """Background task to process document."""
    try:
        # Update status
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            print(f"Document {document_id} not found")
            return
            
        doc.processing_status = "processing"
        db.commit()
        
        # Process document
        print(f"Processing document {document_id}: {file_path}")
        result = await doc_processor.process_document(file_path)
        
        # Add to vector store
        print(f"Adding {len(result['chunks'])} chunks to vector store...")
        chunk_count = await rag_engine.add_document_chunks(
            chunks=result["chunks"],
            document_id=document_id,
            metadata=result["metadata"]
        )
        
        # Extract keywords from document
        print(f"Extracting keywords from document...")
        concepts = await keyword_extractor.get_document_concepts(result["text"])
        
        # Update document
        doc.chunk_count = chunk_count
        doc.processing_status = "completed"
        doc.metadata = result["metadata"]
        db.commit()
        
        print(f"✅ Document {document_id} processed successfully!")
        
    except Exception as e:
        print(f"❌ Error processing document {document_id}: {str(e)}")
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.processing_status = "failed"
            doc.metadata = {"error": str(e)}
            db.commit()


@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload and process a research paper."""
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Create upload directory if not exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # Save file
    file_path = os.path.join(settings.UPLOAD_DIR, f"{datetime.now().timestamp()}_{file.filename}")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Create document record
    document = Document(
        title=file.filename,
        file_path=file_path,
        processing_status="pending"
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # Process in background
    background_tasks.add_task(process_document_background, document.id, file_path, db)
    
    return {
        "id": document.id,
        "filename": file.filename,
        "status": "processing",
        "message": "Document uploaded successfully and processing in background"
    }


@router.get("/")
async def get_documents(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get list of uploaded documents."""
    documents = db.query(Document).offset(skip).limit(limit).all()
    
    return {
        "documents": [
            {
                "id": doc.id,
                "title": doc.metadata.get("title", doc.title) if doc.metadata else doc.title,
                "source": doc.source,
                "upload_date": doc.upload_date.isoformat(),
                "status": doc.processing_status,
                "chunk_count": doc.chunk_count,
                "entity_count": doc.entity_count
            }
            for doc in documents
        ],
        "total": db.query(Document).count()
    }


@router.get("/{document_id}")
async def get_document(document_id: int, db: Session = Depends(get_db)):
    """Get document details."""
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {
        "id": document.id,
        "title": document.metadata.get("title", document.title) if document.metadata else document.title,
        "source": document.source,
        "file_path": document.file_path,
        "upload_date": document.upload_date.isoformat(),
        "metadata": document.metadata,
        "processing_status": document.processing_status,
        "chunk_count": document.chunk_count,
        "entity_count": document.entity_count
    }


@router.delete("/{document_id}")
async def delete_document(document_id: int, db: Session = Depends(get_db)):
    """Delete a document and all its data."""
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete from vector store
    await rag_engine.delete_document(document_id)
    
    # Delete file
    if document.file_path and os.path.exists(document.file_path):
        os.remove(document.file_path)
    
    # Delete from database
    db.delete(document)
    db.commit()
    
    return {"message": "Document deleted successfully"}


@router.get("/stats/overview")
async def get_stats():
    """Get document processing statistics."""
    try:
        vector_stats = rag_engine.get_stats()
        return {
            "vector_store": vector_stats,
            "knowledge_graph": {
                "nodes": 0,
                "edges": 0,
                "density": 0.0,
                "communities": 0
            }
        }
    except Exception as e:
        return {
            "vector_store": {"total_chunks": 0},
            "knowledge_graph": {
                "nodes": 0,
                "edges": 0,
                "density": 0.0,
                "communities": 0
            }
        }
