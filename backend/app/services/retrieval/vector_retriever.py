"""Vector retriever using FAISS."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

import numpy as np

from app.config import get_settings
from app.services.model_gateway import EmbeddingRequest, create_gateway

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run a coroutine from sync code, tolerating threads with no current
    event loop. `asyncio.get_event_loop()` raises RuntimeError once a prior
    `asyncio.run()`/loop has closed on this thread (e.g. after any other
    async test or request already ran) — that used to be swallowed by the
    caller's broad except and silently returned zero results.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("event loop is closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class VectorRetriever:
    """Dense vector retrieval using FAISS."""

    def __init__(
        self,
        dimension: Optional[int] = None,
        index_path: Optional[str] = None,
        gateway: Optional[object] = None,
    ):
        """Initialize vector retriever.

        Args:
            dimension: Embedding dimension. Defaults to settings.EMBEDDING_DIM;
                the index is still rebuilt automatically if the embedding
                provider ever returns a different dimension at runtime.
            index_path: Optional path to save/load index
            gateway: Optional pre-built ModelGateway (e.g. FakeProvider for
                tests). Defaults to the configured provider via create_gateway().
        """
        self.dimension = dimension or get_settings().EMBEDDING_DIM
        self.index_path = index_path
        self._index = None
        self._doc_store: Dict[int, Dict[str, Any]] = {}
        self._gateway = gateway or create_gateway()
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
                result = _run_async(
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
        actual_dim = int(embeddings.shape[1])

        if actual_dim != self.dimension:
            # The embedding provider returned a different dimension than the
            # index was built for (e.g. a provider fallback/switch mid-run).
            # Rebuild the index at the new dimension and re-embed whatever
            # was already stored, instead of crashing on faiss.add().
            logger.warning(
                "Vector index dimension changed from %s to %s; rebuilding "
                "index and re-embedding %d stored document(s).",
                self.dimension, actual_dim, len(self._doc_store),
            )
            import faiss
            previous_docs = [self._doc_store[i] for i in sorted(self._doc_store)]
            self.dimension = actual_dim
            self._index = faiss.IndexFlatIP(actual_dim)
            self._doc_store = {}
            if previous_docs:
                self.add_documents(previous_docs, batch_size=batch_size)

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
            result = _run_async(
                self._gateway.embed(EmbeddingRequest(texts=[query], purpose="query"))
            )
            query_embedding = np.array(result.embeddings[0], dtype=np.float32).reshape(1, -1)
            # Normalize
            query_embedding = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)
        except Exception as e:
            logger.error(f"Query embedding failed: {e}")
            return []

        if query_embedding.shape[1] != self._index.d:
            logger.warning(
                "Query embedding dim %d does not match vector index dim %d "
                "(embedding provider changed); skipping vector retrieval for this query.",
                query_embedding.shape[1], self._index.d,
            )
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
