"""LLM-based reranker for retrieval results."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.services.model_gateway import (
    ChatMessage,
    GenerationRequest,
    GenerationResult,
    create_gateway,
)

logger = logging.getLogger(__name__)


class LLMReranker:
    """LLM-based reranker for retrieval results."""

    RERANK_PROMPT = """You are a reranker. Given a query and a list of documents, score each document from 0.0 to 1.0 based on relevance.

Query: {query}

Documents:
{documents}

Respond ONLY with a JSON array of scores in the same order as the documents:
[score1, score2, score3, ...]

Example: [0.9, 0.3, 0.7, 0.5]
"""

    def __init__(self, gateway=None):
        """Initialize LLM reranker.

        Args:
            gateway: Optional model gateway instance
        """
        self._gateway = gateway or create_gateway()

    async def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: Optional[int] = None,
        batch_size: int = 10,
    ) -> List[Dict[str, Any]]:
        """Rerank documents by relevance to query.

        Args:
            query: Query text
            documents: List of document texts
            top_k: Number of results to return (None = all)
            batch_size: Batch size for reranking

        Returns:
            List of documents with rerank scores
        """
        if not documents:
            return []

        all_scores = []

        # Process in batches to avoid token limits
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i : i + batch_size]

            # Format documents for prompt
            doc_text = "\n\n".join([f"[{j}] {doc}" for j, doc in enumerate(batch_docs)])
            prompt = self.RERANK_PROMPT.format(
                query=query,
                documents=doc_text,
            )

            try:
                result = await self._gateway.generate(
                    GenerationRequest(
                        messages=[
                            ChatMessage(role="system", content="You are a helpful assistant that scores document relevance."),
                            ChatMessage(role="user", content=prompt),
                        ],
                        temperature=0.0,
                        max_tokens=200,
                        json_mode=True,
                    )
                )

                scores = self._parse_scores(result.text, len(batch_docs))
                all_scores.extend(scores)

            except Exception as e:
                logger.error(f"Reranking failed: {e}")
                # Fallback: return uniform scores
                all_scores.extend([0.5] * len(batch_docs))

        # Attach scores to documents
        results = []
        for i, (doc, score) in enumerate(zip(documents, all_scores)):
            results.append({
                "text": doc,
                "rerank_score": score,
                "original_index": i,
            })

        # Sort by rerank score descending
        results.sort(key=lambda x: x["rerank_score"], reverse=True)

        if top_k:
            results = results[:top_k]

        return results

    def _parse_scores(self, text: str, expected_count: int) -> List[float]:
        """Parse LLM output into scores."""
        import json
        import re

        # Try to extract JSON array
        match = re.search(r"\[.*?\]", text, re.DOTALL)
        if match:
            try:
                scores = json.loads(match.group())
                if len(scores) == expected_count:
                    return [float(s) for s in scores]
            except (json.JSONDecodeError, ValueError):
                pass

        # Fallback: extract numbers
        numbers = re.findall(r"[\d.]+", text)
        scores = []
        for n in numbers[:expected_count]:
            try:
                scores.append(float(n))
            except ValueError:
                scores.append(0.5)

        # Pad if needed
        while len(scores) < expected_count:
            scores.append(0.5)

        return scores[:expected_count]


def quick_rerank(
    query: str,
    documents: List[Dict[str, Any]],
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """Quick heuristic rerank without LLM.

    Uses keyword overlap and score boosting.

    Args:
        query: Query text
        documents: List of documents with 'text' and 'score'
        top_k: Number of results to return

    Returns:
        Reranked documents
    """
    query_terms = set(query.lower().split())

    results = []
    for doc in documents:
        text = doc.get("text", "")
        doc_terms = set(text.lower().split())

        # Keyword overlap
        overlap = len(query_terms & doc_terms)
        overlap_score = overlap / (len(query_terms) + 1)

        # Combine with original score
        original_score = doc.get("score", 0.0)
        new_score = 0.5 * original_score + 0.5 * overlap_score

        results.append({
            **doc,
            "rerank_score": new_score,
        })

    results.sort(key=lambda x: x["rerank_score"], reverse=True)
    return results[:top_k]
