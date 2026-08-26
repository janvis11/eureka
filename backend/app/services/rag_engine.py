"""
Simple RAG Engine: semantic search + LLM answer generation.
Uses FAISS for vector storage, ModelGateway for embeddings and generation.
"""

from typing import List, Dict, Any, Optional
import faiss
import numpy as np
import os
import asyncio
from app.config import get_settings
from app.services.model_gateway.base import (
    ChatMessage,
    EmbeddingRequest,
    GenerationRequest,
)
from app.services.retrieval.confidence import compute_confidence
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class RAGEngine:
    """Retrieval-Augmented Generation using FAISS + ModelGateway."""

    def __init__(self, gateway: Optional[object] = None):
        self.settings = settings

        # Initialize FAISS index
        self.embedding_dim = settings.EMBEDDING_DIM
        self.index = faiss.IndexFlatL2(self.embedding_dim)

        # Store document texts and metadata
        self.documents = []
        self.metadatas = []
        self.doc_ids = []

        # FAISS index file path
        self.index_path = os.path.join(settings.CHROMADB_PATH, "faiss_index.bin")
        self.metadata_path = os.path.join(settings.CHROMADB_PATH, "metadata.pkl")

        # Create data directory if needed
        os.makedirs(settings.CHROMADB_PATH, exist_ok=True)

        # Load existing index if available
        self._load_index()

        # Use provided gateway or shared singleton
        if gateway is not None:
            self.gateway = gateway
        else:
            from app.services.shared import get_gateway
            self.gateway = get_gateway()

        logger.info("RAG Engine initialized with FAISS")

    def _load_index(self):
        """Load persisted FAISS index and metadata."""
        try:
            if os.path.exists(self.index_path):
                self.index = faiss.read_index(self.index_path)
                self.embedding_dim = int(self.index.d)
                logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors")

                # Load metadata
                if os.path.exists(self.metadata_path):
                    import pickle
                    with open(self.metadata_path, 'rb') as f:
                        data = pickle.load(f)
                        self.documents = data.get('documents', [])
                        self.metadatas = data.get('metadatas', [])
                        self.doc_ids = data.get('doc_ids', [])
                    logger.info(f"Loaded {len(self.documents)} documents")
        except Exception as e:
            logger.warning(f"Could not load index: {e}, starting fresh")

    def _index_dimension(self) -> int:
        """Return the active FAISS vector dimension."""
        return int(getattr(self.index, "d", self.embedding_dim))

    def _replace_index(self, dimension: int) -> None:
        """Replace FAISS index with a new empty index of the given dimension."""
        self.embedding_dim = dimension
        self.index = faiss.IndexFlatL2(dimension)

    async def _ensure_index_dimension(self, dimension: int) -> None:
        """Keep FAISS dimension aligned with the embedding provider.

        API embeddings and local fallback embeddings can have different
        dimensions. If the provider changes after a quota/network failure,
        rebuild existing stored texts with the currently active embedder.
        """
        current_dim = self._index_dimension()
        if current_dim == dimension:
            return

        if self.index.ntotal == 0:
            logger.info(f"Updating embedding dim: {current_dim} -> {dimension}")
            self._replace_index(dimension)
            return

        logger.warning(
            "Embedding dimension changed from %s to %s; rebuilding FAISS "
            "index with the active embedding provider.",
            current_dim,
            dimension,
        )
        old_documents = list(self.documents)
        if not old_documents:
            self._replace_index(dimension)
            return

        embeddings = await self._embed_texts(old_documents)
        embeddings_array = np.array(embeddings, dtype=np.float32)
        rebuilt_dim = int(embeddings_array.shape[1])
        self._replace_index(rebuilt_dim)
        self.index.add(embeddings_array)

    def _save_index(self):
        """Persist FAISS index and metadata to disk."""
        try:
            os.makedirs(settings.CHROMADB_PATH, exist_ok=True)
            faiss.write_index(self.index, self.index_path)

            # Save metadata
            import pickle
            with open(self.metadata_path, 'wb') as f:
                pickle.dump({
                    'documents': self.documents,
                    'metadatas': self.metadatas,
                    'doc_ids': self.doc_ids
                }, f)
            logger.info("Index saved to disk")
        except Exception as e:
            logger.error(f"Error saving index: {e}")

    async def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed texts via the model gateway."""
        result = await self.gateway.embed(EmbeddingRequest(texts=texts, purpose="document"))
        return result.embeddings

    async def _embed_text(self, text: str) -> List[float]:
        """Embed a single text via the model gateway."""
        result = await self.gateway.embed(EmbeddingRequest(texts=[text], purpose="query"))
        return result.embeddings[0]

    async def add_document_chunks(
        self,
        chunks: List[Dict[str, Any]],
        document_id: int,
        metadata: Dict[str, Any]
    ) -> int:
        """Add document chunks to vector store."""
        try:
            texts = []
            metadatas = []
            ids = []

            for i, chunk in enumerate(chunks):
                text = chunk.get("text", "")
                if not text.strip():
                    logger.warning(f"Skipping empty chunk {i} for document {document_id}")
                    continue

                # Prepare metadata
                chunk_metadata = {
                    "document_id": str(document_id),
                    "chunk_index": chunk.get("chunk_index", i),
                    "document_title": metadata.get("title", "Unknown"),
                    "page_count": metadata.get("page_count", 0)
                }

                texts.append(text)
                metadatas.append(chunk_metadata)
                ids.append(f"doc_{document_id}_chunk_{i}")

            # Create embeddings in batch via gateway
            if texts:
                logger.info(f"Generating embeddings for {len(texts)} chunks...")
                embeddings = await self._embed_texts(texts)

                # Convert to numpy array and reshape if needed
                embeddings_array = np.array(embeddings, dtype=np.float32)

                await self._ensure_index_dimension(int(embeddings_array.shape[1]))

                # Add to FAISS index
                self.index.add(embeddings_array)

                # Store documents and metadata
                self.documents.extend(texts)
                self.metadatas.extend(metadatas)
                self.doc_ids.extend(ids)

                # Save to disk
                self._save_index()

                logger.info(f"Added {len(texts)} chunks from document {document_id} to vector store")
                return len(texts)

            logger.warning(f"No valid chunks to add for document {document_id}")
            return 0

        except Exception as e:
            logger.error(f"Error adding document chunks: {e}", exc_info=True)
            raise

    async def semantic_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant document chunks."""
        try:
            if self.index.ntotal == 0:
                if self.documents:
                    await self._rebuild_index()
                    self._save_index()
                if self.index.ntotal == 0:
                    logger.warning("No documents in index")
                    return []

            # Create query embedding via gateway
            query_embedding = await self._embed_text(query)
            query_array = np.array([query_embedding], dtype=np.float32)

            if query_array.shape[1] != self._index_dimension():
                await self._ensure_index_dimension(int(query_array.shape[1]))
                self._save_index()
            if query_array.shape[1] != self._index_dimension():
                logger.warning("No documents in index")
                return []

            # Search in FAISS
            distances, indices = self.index.search(query_array, min(top_k, self.index.ntotal))

            # Format results
            formatted_results = []
            for i, idx in enumerate(indices[0]):
                if idx >= 0 and idx < len(self.documents):
                    formatted_results.append({
                        "text": self.documents[idx],
                        "metadata": self.metadatas[idx],
                        "distance": float(distances[0][i])
                    })

            return formatted_results

        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []

    async def generate_answer(
        self,
        question: str,
        context: List[Dict[str, Any]],
        max_tokens: int = None
    ) -> Dict[str, Any]:
        """Generate answer using LLM with retrieved context.

        Abstains instead of calling the LLM when retrieval confidence is
        below settings.ABSTENTION_CONFIDENCE_THRESHOLD — a weak retrieval
        can't produce a trustworthy answer no matter how fluent the LLM
        makes it sound, so the gate runs before generation, not after.
        """
        try:
            if not context:
                return {
                    "answer": "No relevant information found in the uploaded documents.",
                    "confidence": 0.0,
                    "abstained": True,
                    "reason": "no_evidence_retrieved",
                }

            confidence_result = compute_confidence(
                context, threshold=self.settings.ABSTENTION_CONFIDENCE_THRESHOLD
            )
            if not confidence_result.should_answer:
                return {
                    "answer": (
                        "I don't have enough confident evidence to answer this. "
                        + (confidence_result.what_would_help or "")
                    ),
                    "confidence": round(confidence_result.score, 2),
                    "abstained": True,
                    "reason": confidence_result.reason,
                    "confidence_signals": confidence_result.signals,
                    "closest_evidence": [
                        {
                            "text": c.get("text", "")[:200],
                            "document_id": c.get("metadata", {}).get("document_id"),
                            "distance": c.get("distance"),
                        }
                        for c in context[:3]
                    ],
                    "what_would_help": confidence_result.what_would_help,
                }

            # Build context string
            context_text = "\n\n".join([
                f"Source {i+1} (Distance: {c.get('distance', 0):.4f}):\n{c.get('text', '')}"
                for i, c in enumerate(context[:3])
            ])

            # Create prompt
            prompt = f"""You are a research assistant. Answer the following question based on the provided context.

QUESTION: {question}

CONTEXT:
{context_text}

INSTRUCTIONS:
1. Answer the question directly and concisely
2. Only use information from the context
3. If the answer is not in the context, say "I don't have enough information"
4. Be accurate and avoid speculation

ANSWER:"""

            # Call gateway
            result = await self.gateway.generate(
                GenerationRequest(
                    messages=[ChatMessage(role="user", content=prompt)],
                    temperature=self.settings.LLM_TEMPERATURE,
                    max_tokens=max_tokens or self.settings.LLM_MAX_TOKENS,
                )
            )

            answer = result.text

            return {
                "answer": answer,
                "confidence": round(confidence_result.score, 2),
                "abstained": False,
                "confidence_signals": confidence_result.signals,
            }

        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return {
                "answer": f"Error generating answer: {str(e)}",
                "confidence": 0.0
            }

    async def delete_document(self, document_id: int) -> bool:
        """Delete document from vector store."""
        try:
            # Find all chunks for this document
            indices_to_remove = []
            for i, metadata in enumerate(self.metadatas):
                if metadata.get("document_id") == str(document_id):
                    indices_to_remove.append(i)

            if not indices_to_remove:
                logger.warning(f"No chunks found for document {document_id}")
                return False

            # FAISS doesn't support direct deletion, so we rebuild the index
            # Remove in reverse order to maintain indices
            for idx in sorted(indices_to_remove, reverse=True):
                del self.documents[idx]
                del self.metadatas[idx]
                del self.doc_ids[idx]

            # Rebuild index
            await self._rebuild_index()
            self._save_index()

            logger.info(f"Deleted document {document_id} from vector store")
            return True

        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return False

    async def _rebuild_index(self):
        """Rebuild FAISS index from stored documents."""
        try:
            # Re-embed all documents
            if self.documents:
                embeddings = await self._embed_texts(self.documents)
                embeddings_array = np.array(embeddings, dtype=np.float32)
                self._replace_index(int(embeddings_array.shape[1]))
                self.index.add(embeddings_array)
                logger.info(f"Rebuilt index with {self.index.ntotal} vectors")
            else:
                self._replace_index(self.embedding_dim)
        except Exception as e:
            logger.error(f"Error rebuilding index: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        return {
            "total_chunks": self.index.ntotal,
            "total_documents": len(set([m.get("document_id") for m in self.metadatas])),
            "embedding_dim": self.embedding_dim,
            "index_type": "FAISS"
        }
