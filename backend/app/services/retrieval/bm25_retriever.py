"""BM25 lexical retriever."""

from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple


class BM25Retriever:
    """BM25 lexical retrieval with in-memory index."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """Initialize BM25 retriever.

        Args:
            k1: Term frequency saturation parameter (default 1.5)
            b: Length normalization parameter (default 0.75)
        """
        self.k1 = k1
        self.b = b
        self.documents: Dict[str, str] = {}
        self.doc_lengths: Dict[str, float] = {}
        self.avg_doc_length: float = 0.0
        self.idf: Dict[str, float] = {}
        self.term_freq: Dict[str, Dict[str, int]] = defaultdict(dict)
        self._total_docs: int = 0

    def add_document(self, doc_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a document to the index."""
        self.documents[doc_id] = text
        tokens = self._tokenize(text)
        self.doc_lengths[doc_id] = len(tokens)
        self._total_docs += 1

        # Update average document length
        total_length = sum(self.doc_lengths.values())
        self.avg_doc_length = total_length / self._total_docs if self._total_docs > 0 else 0

        # Update term frequencies
        for token in tokens:
            self.term_freq[token][doc_id] = self.term_freq[token].get(doc_id, 0) + 1

        # Update IDF
        self._update_idf(tokens)

    def _update_idf(self, tokens: List[str]) -> None:
        """Update IDF values for tokens."""
        unique_tokens = set(tokens)
        for token in unique_tokens:
            df = len(self.term_freq[token])
            self.idf[token] = math.log((self._total_docs - df + 0.5) / (df + 0.5) + 1)

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into tokens."""
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        return [t for t in tokens if len(t) > 1]

    def search(
        self,
        query: str,
        top_k: int = 10,
        filter_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for documents matching the query."""
        query_tokens = self._tokenize(query)

        if not query_tokens:
            return []

        scores: Dict[str, float] = defaultdict(float)
        doc_ids = filter_ids or list(self.documents.keys())

        for doc_id in doc_ids:
            if doc_id not in self.documents:
                continue

            doc_len = self.doc_lengths.get(doc_id, 0)
            score = 0.0

            for token in query_tokens:
                if token not in self.term_freq:
                    continue

                tf = self.term_freq[token].get(doc_id, 0)
                idf = self.idf.get(token, 0)

                # BM25 scoring formula
                tf_sat = tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_length))
                score += idf * tf_sat

            if score > 0:
                scores[doc_id] = score

        # Sort by score descending
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        return [
            {
                "doc_id": doc_id,
                "text": self.documents[doc_id],
                "score": score,
                "retriever": "bm25",
            }
            for doc_id, score in sorted_docs
        ]

    def bulk_add(self, documents: List[Tuple[str, str, Optional[Dict[str, Any]]]]) -> None:
        """Add multiple documents to the index."""
        for doc_id, text, metadata in documents:
            self.add_document(doc_id, text, metadata)

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        return {
            "total_documents": self._total_docs,
            "vocabulary_size": len(self.term_freq),
            "avg_document_length": self.avg_doc_length,
        }
