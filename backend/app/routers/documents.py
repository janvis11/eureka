from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
from datetime import datetime
import logging

from app.models.database import SessionLocal, get_db

logger = logging.getLogger(__name__)
from app.models.models import Document
from app.services.document_processor import DocumentProcessor
from app.services.rag_engine import RAGEngine
from app.services.knowledge_graph import KeywordExtractor
from app.services.shared import get_gateway
from app.config import get_settings

router = APIRouter(tags=["documents"])
settings = get_settings()

# Initialize services
doc_processor = DocumentProcessor(
    chunk_size=settings.CHUNK_SIZE,
    chunk_overlap=settings.CHUNK_OVERLAP
)
_gateway = get_gateway()
rag_engine = RAGEngine(gateway=_gateway)
keyword_extractor = KeywordExtractor(gateway=_gateway)

# Structural RAG engine (PageIndex-inspired)
from app.services.retrieval.structural_rag_engine import get_structural_engine
structural_engine = get_structural_engine(gateway=_gateway)


async def process_document_background(document_id: int, file_path: str):
    """Background task to process document with structural indexing."""
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.error(f"Document {document_id} not found")
            return

        doc.processing_status = "processing"
        db.commit()

        logger.info(f"Processing document {document_id}: {file_path}")

        section_count = 0
        vector_status = "not_started"

        # ----------------------------------------------------------------
        # Step 1: Extract document structure (PageIndex-inspired)
        # ----------------------------------------------------------------
        doc_id_str = str(document_id)
        try:
            section_tree = await doc_processor.extract_structure(
                file_path=file_path,
                doc_id=doc_id_str,
            )
            structural_engine.index_document(doc_id_str, section_tree)
            section_count = section_tree.total_sections
            logger.info(
                f"Structural index built for doc {document_id}: "
                f"{section_count} sections"
            )
        except Exception as e:
            logger.warning(f"Structural extraction failed for {document_id}: {e} — using chunk fallback")

        # ----------------------------------------------------------------
        # Step 2: Traditional chunking + vector store (fallback retrieval)
        # ----------------------------------------------------------------
        result = await doc_processor.process_document(file_path)

        try:
            chunk_count = await rag_engine.add_document_chunks(
                chunks=result["chunks"],
                document_id=document_id,
                metadata=result["metadata"]
            )
            vector_status = "indexed"
        except Exception as e:
            chunk_count = 0
            vector_status = f"failed: {e}"
            logger.error(
                "Vector indexing failed for document %s; keeping extracted "
                "document available through structural and graph paths.",
                document_id,
                exc_info=True,
            )

        # ----------------------------------------------------------------
        # Step 3: Extract concepts + write provenance-rich graph
        # ----------------------------------------------------------------
        concepts = await keyword_extractor.get_document_concepts(result["text"])
        graph_counts = {
            "documents": 0,
            "chunks": 0,
            "entities": 0,
            "claims": 0,
            "relationships": 0,
        }

        try:
            from app.services.graph.neo4j_client import get_neo4j_client
            from app.services.graph.repository import GraphRepository
            from app.services.graph.ingestion import GraphIngestionPipeline

            neo4j_client = get_neo4j_client()
            if not neo4j_client.is_connected:
                await neo4j_client.connect()

            if neo4j_client.is_connected:
                graph_repo = GraphRepository(neo4j_client)
                graph_ingestion = GraphIngestionPipeline(
                    repository=graph_repo,
                    gateway=_gateway,
                    keyword_extractor=keyword_extractor,
                )
                graph_counts = await graph_ingestion.ingest_document(
                    document_id=doc_id_str,
                    title=result["metadata"].get("title", doc.title or "Unknown"),
                    metadata=result["metadata"],
                    chunks=result["chunks"],
                    full_text=result["text"],
                    source_type="pdf",
                )
                logger.info(f"Document {document_id} written to knowledge graph: {graph_counts}")
        except Exception as e:
            logger.warning(f"Knowledge graph write skipped (Neo4j unavailable): {e}")

        # ----------------------------------------------------------------
        # Step 4: Update DB record
        # ----------------------------------------------------------------
        doc.chunk_count = chunk_count
        doc.processing_status = "completed"
        doc.doc_metadata = {
            **result["metadata"],
            "structural_sections": section_count,
            "vector_status": vector_status,
            "concepts": concepts,
            "graph_counts": graph_counts,
        }
        db.commit()

        logger.info(f"Document {document_id} processed successfully!")

    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}")
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.processing_status = "failed"
            doc.doc_metadata = {"error": str(e)}
            db.commit()
    finally:
        db.close()


def _validate_upload(file: UploadFile) -> int:
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds limit. Maximum size: {settings.MAX_UPLOAD_SIZE // (1024*1024)}MB"
        )

    if file_size == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    return file_size


def _save_upload(file: UploadFile) -> str:
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    safe_filename = "".join(c for c in file.filename or "paper.pdf" if c.isalnum() or c in ('.', '-', '_'))
    file_path = os.path.join(settings.UPLOAD_DIR, f"{datetime.now().timestamp()}_{safe_filename}")

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")

    return file_path


def _create_document_record(file: UploadFile, file_path: str, db: Session) -> Document:
    document = Document(
        title=file.filename,
        file_path=file_path,
        processing_status="pending"
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


async def _queue_upload(background_tasks: BackgroundTasks, file: UploadFile, db: Session) -> dict:
    _validate_upload(file)
    file_path = _save_upload(file)
    document = _create_document_record(file, file_path, db)

    background_tasks.add_task(process_document_background, document.id, file_path)

    return {
        "id": document.id,
        "filename": file.filename,
        "status": "processing",
        "message": "Document uploaded and being processed with structural indexing and graph extraction",
        "features": ["structural_rag", "vector_fallback", "knowledge_graph", "claim_graph"],
    }


@router.post("/documents/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload and process a research paper."""
    return await _queue_upload(background_tasks, file, db)


@router.post("/documents/upload/batch")
async def upload_documents_batch(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """Upload and process many research papers in one request."""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    results = []
    for file in files:
        results.append(await _queue_upload(background_tasks, file, db))

    return {
        "documents": results,
        "total": len(results),
        "message": "Batch upload accepted; papers are being processed in the background",
    }


@router.get("/documents")
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
                "title": doc.doc_metadata.get("title", doc.title) if doc.doc_metadata else doc.title,
                "source": doc.source,
                "upload_date": doc.upload_date.isoformat(),
                "status": doc.processing_status,
                "chunk_count": doc.chunk_count,
                "structural_sections": (doc.doc_metadata or {}).get("structural_sections", 0),
            }
            for doc in documents
        ],
        "total": db.query(Document).count()
    }


@router.get("/documents/structural-index/stats")
@router.get("/structural-index/stats")
async def get_structural_index_stats():
    """Get stats about the structural (PageIndex-style) index."""
    return structural_engine.get_stats()


@router.get("/documents/{document_id}")
@router.get("/{document_id}")
async def get_document(document_id: int, db: Session = Depends(get_db)):
    """Get document details."""
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": document.id,
        "title": document.doc_metadata.get("title", document.title) if document.doc_metadata else document.title,
        "source": document.source,
        "file_path": document.file_path,
        "upload_date": document.upload_date.isoformat(),
        "metadata": document.doc_metadata,
        "processing_status": document.processing_status,
        "chunk_count": document.chunk_count
    }


@router.delete("/documents/{document_id}")
@router.delete("/{document_id}")
async def delete_document(document_id: int, db: Session = Depends(get_db)):
    """Delete a document and all its data."""
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete from vector store
    await rag_engine.delete_document(document_id)

    # Delete from structural index
    structural_engine.remove_document(str(document_id))

    # Delete from Neo4j graph when available. This keeps deleted papers from
    # leaving stale document/chunk/claim nodes in graph-native discovery.
    graph_delete_counts = None
    try:
        from app.services.graph.neo4j_client import get_neo4j_client
        from app.services.graph.repository import GraphRepository

        neo4j_client = get_neo4j_client()
        if not neo4j_client.is_connected:
            await neo4j_client.connect()
        graph_delete_counts = await GraphRepository(neo4j_client).delete_document(str(document_id))
    except Exception as e:
        logger.warning(f"Knowledge graph delete skipped for document {document_id}: {e}")

    # Delete file
    if document.file_path and os.path.exists(document.file_path):
        os.remove(document.file_path)

    db.delete(document)
    db.commit()

    return {
        "message": "Document deleted successfully",
        "graph_delete_counts": graph_delete_counts,
    }


@router.get("/documents/stats/overview")
@router.get("/stats/overview")
async def get_stats():
    """Get document processing statistics."""
    try:
        vector_stats = rag_engine.get_stats()
        structural_stats = structural_engine.get_stats()
        knowledge_graph = {
            "nodes": 0,
            "edges": 0,
            "density": 0.0,
            "communities": 0
        }
        try:
            from app.services.graph.neo4j_client import get_neo4j_client
            from app.services.graph.repository import GraphRepository

            neo4j_client = get_neo4j_client()
            if not neo4j_client.is_connected:
                await neo4j_client.connect()

            graph_stats = await GraphRepository(neo4j_client).get_stats()
            node_count = (
                graph_stats.get("documents", 0)
                + graph_stats.get("chunks", 0)
                + graph_stats.get("entities", 0)
                + graph_stats.get("claims", 0)
                + graph_stats.get("hypotheses", 0)
            )
            edge_count = graph_stats.get("relationships", 0)
            knowledge_graph = {
                "nodes": node_count,
                "edges": edge_count,
                "density": edge_count / max(1, node_count * node_count),
                "communities": max(0, graph_stats.get("documents", 0)),
            }
        except Exception as e:
            logger.info(f"Knowledge graph stats unavailable: {e}")

        return {
            "vector_store": vector_stats,
            "structural_index": structural_stats,
            "knowledge_graph": knowledge_graph
        }
    except Exception as e:
        return {
            "vector_store": {"total_chunks": 0},
            "structural_index": {"indexed_documents": 0},
            "knowledge_graph": {
                "nodes": 0,
                "edges": 0,
                "density": 0.0,
                "communities": 0
            }
        }
