"""Vector retriever using FAISS."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np

from app.services.model_gateway import EmbeddingRequest, create_gateway

logger = logging.getLogger(__name__)


class VectorRetriever:
    """Dense vector retrieval using FAISS."""

    def __init__(self, dimension: int = 384, index_path: Optional[str] = None):
        """Initialize vector retriever.

        Args:
            dimension: Embedding dimension
            index_path: Optional path to save/load index
        """
        self.dimension = dimension
        self.index_path = index_path
        self._index = None
        self._doc_store: Dict[int, Dict[str, Any]] = {}
        self._gateway = create_gateway()
        self._initialized = False

    def _ensure_index(self) -> None:
        """Ensure FAISS index is initialized."""
        try:
            import faiss

            if self._index is None:
                self._index = faiss.IndexFlatIP(self.dimension)  # Inner product for cosine similarity
                self._initialized = True
        except ImportError:
            logger.warning("FAISS not available. Vector retrieval disabled.")
            self._initialized = False

    def add_documents(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 100,
    ) -> int:
        """Add documents to the index.

        Args:
            documents: List of dicts with 'text' and optional 'metadata'
            batch_size: Batch size for embedding generation

        Returns:
            Number of documents added
        """
        self._ensure_index()
        if not self._initialized:
            return 0

        texts = [doc.get("text", "") for doc in documents]
        metadata_list = [doc.get("metadata", {}) for doc in documents]

        # Generate embeddings in batches
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                result = loop.run_until_complete(
                    self._gateway.embed(EmbeddingRequest(texts=batch_texts))
                )
                embeddings = np.array(result.embeddings, dtype=np.float32)
                # Normalize for cosine similarity
                norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
                embeddings = embeddings / (norms + 1e-8)
                all_embeddings.append(embeddings)
            except Exception as e:
                logger.error(f"Embedding generation failed: {e}")
                continue

        if not all_embeddings:
            return 0

        embeddings = np.vstack(all_embeddings)

        # Add to FAISS index
        start_idx = len(self._doc_store)
        self._index.add(embeddings)

        # Store document metadata
        for i, (text, metadata) in enumerate(zip(texts, metadata_list)):
            doc_idx = start_idx + i
            self._doc_store[doc_idx] = {
                "text": text,
                "metadata": metadata,
            }

        return len(texts)

    def search(
        self,
        query: str,
        top_k: int = 10,
        filter_fn: Optional[callable] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar documents.

        Args:
            query: Query text
            top_k: Number of results to return
            filter_fn: Optional filter function

        Returns:
            List of results with text, metadata, and score
        """
        self._ensure_index()
        if not self._initialized or self._index.ntotal == 0:
            return []

        try:
            import asyncio
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(
                self._gateway.embed(EmbeddingRequest(texts=[query], purpose="query"))
            )
            query_embedding = np.array(result.embeddings[0], dtype=np.float32).reshape(1, -1)
            # Normalize
            query_embedding = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)
        except Exception as e:
            logger.error(f"Query embedding failed: {e}")
            return []

        # Search FAISS index
        distances, indices = self._index.search(query_embedding, top_k * 2)  # Get extra for filtering

        results = []
        for i, (doc_idx, score) in enumerate(zip(indices[0], distances[0])):
            if doc_idx < 0 or doc_idx not in self._doc_store:
                continue

            doc = self._doc_store[doc_idx]

            # Apply filter if provided
            if filter_fn and not filter_fn(doc):
                continue

            results.append({
                "text": doc["text"],
                "metadata": doc.get("metadata", {}),
                "score": float(score),
                "retriever": "vector",
            })

            if len(results) >= top_k:
                break

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        if not self._initialized or self._index is None:
            return {"total_documents": 0}

        return {
            "total_documents": self._index.ntotal,
            "dimension": self.dimension,
        }

    def save(self, path: Optional[str] = None) -> None:
        """Save index to disk."""
        try:
            import faiss
            import pickle

            path = path or self.index_path
            if path:
                faiss.write_index(self._index, f"{path}.faiss")
                with open(f"{path}.pkl", "wb") as f:
                    pickle.dump(self._doc_store, f)
        except Exception as e:
            logger.error(f"Failed to save index: {e}")

    def load(self, path: Optional[str] = None) -> bool:
        """Load index from disk."""
        try:
            import faiss
            import pickle

            path = path or self.index_path
            if path and faiss.get_index_type(f"{path}.faiss"):
                self._index = faiss.read_index(f"{path}.faiss")
                with open(f"{path}.pkl", "rb") as f:
                    self._doc_store = pickle.load(f)
                self._initialized = True
                return True
        except Exception as e:
            logger.warning(f"Failed to load index: {e}")

        return False
