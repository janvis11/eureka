"""Fusion strategies for combining retrieval results."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def reciprocal_rank_fusion(
    result_lists: List[List[Dict[str, Any]]],
    k: int = 60,
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """Reciprocal Rank Fusion of multiple result lists.

    Args:
        result_lists: List of result lists from different retrievers
        k: Ranking constant (default 60)
        top_k: Number of results to return

    Returns:
        Fused and ranked results
    """
    fused_scores: Dict[str, float] = {}
    fused_docs: Dict[str, Dict[str, Any]] = {}

    for results in result_lists:
        for rank, result in enumerate(results, start=1):
            doc_key = _get_doc_key(result)
            if not doc_key:
                continue

            score = 1.0 / (k + rank)

            if doc_key not in fused_scores:
                fused_scores[doc_key] = 0.0
                fused_docs[doc_key] = result
            else:
                fused_scores[doc_key] += score

    # Sort by fused score
    sorted_docs = sorted(
        fused_scores.items(),
        key=lambda x: x[1],
        reverse=True,
    )[:top_k]

    results = []
    for doc_key, score in sorted_docs:
        doc = fused_docs[doc_key].copy()
        doc["fusion_score"] = score
        doc["retrieval_sources"] = _get_retrieval_sources(doc_key, result_lists)
        results.append(doc)

    return results


def _get_doc_key(result: Dict[str, Any]) -> Optional[str]:
    """Extract a unique document key from a result."""
    # Try various key fields
    for key in ["doc_id", "id", "chunk_id", "text"]:
        if key in result and result[key]:
            return str(result[key])
    return None


def _get_retrieval_sources(
    doc_key: str,
    result_lists: List[List[Dict[str, Any]]],
) -> List[str]:
    """Get list of retrievers that returned this document."""
    sources = []
    for results in result_lists:
        for result in results:
            if _get_doc_key(result) == doc_key:
                retriever = result.get("retriever", "unknown")
                if retriever not in sources:
                    sources.append(retriever)
                break
    return sources


def weighted_fusion(
    result_lists: List[List[Dict[str, Any]]],
    weights: Optional[List[float]] = None,
    top_k: int = 10,
    normalize: bool = True,
) -> List[Dict[str, Any]]:
    """Weighted score fusion of multiple result lists.

    Args:
        result_lists: List of result lists from different retrievers
        weights: Weight for each retriever (default: equal weights)
        top_k: Number of results to return
        normalize: Whether to normalize scores to 0-1

    Returns:
        Fused and ranked results
    """
    if not weights:
        weights = [1.0 / len(result_lists)] * len(result_lists)

    # Normalize scores if requested
    if normalize:
        result_lists = [_normalize_scores(results) for results in result_lists]

    fused_scores: Dict[str, float] = {}
    fused_docs: Dict[str, Dict[str, Any]] = {}

    for results, weight in zip(result_lists, weights):
        for result in results:
            doc_key = _get_doc_key(result)
            if not doc_key:
                continue

            score = result.get("score", 0.0) * weight

            if doc_key not in fused_scores:
                fused_scores[doc_key] = 0.0
                fused_docs[doc_key] = result
            else:
                fused_scores[doc_key] += score

    # Sort by fused score
    sorted_docs = sorted(
        fused_scores.items(),
        key=lambda x: x[1],
        reverse=True,
    )[:top_k]

    results = []
    for doc_key, score in sorted_docs:
        doc = fused_docs[doc_key].copy()
        doc["fusion_score"] = score
        doc["retrieval_sources"] = _get_retrieval_sources(doc_key, result_lists)
        results.append(doc)

    return results


def _normalize_scores(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize scores to 0-1 range."""
    if not results:
        return results

    scores = [r.get("score", 0.0) for r in results]
    min_score = min(scores) if scores else 0
    max_score = max(scores) if scores else 1

    if max_score - min_score < 1e-8:
        # All scores are the same
        return results

    normalized = []
    for result in results:
        doc = result.copy()
        raw_score = doc.get("score", 0.0)
        doc["score"] = (raw_score - min_score) / (max_score - min_score)
        normalized.append(doc)

    return normalized


class FusionRetriever:
    """High-level fusion retriever combining multiple strategies."""

    def __init__(
        self,
        strategy: str = "rrf",
        weights: Optional[Dict[str, float]] = None,
    ):
        """Initialize fusion retriever.

        Args:
            strategy: Fusion strategy ('rrf' or 'weighted')
            weights: Optional weights for weighted fusion
        """
        self.strategy = strategy
        self.weights = weights or {}

    def fuse(
        self,
        result_lists: List[List[Dict[str, Any]]],
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """Fuse multiple result lists.

        Args:
            result_lists: List of result lists from different retrievers
            top_k: Number of results to return

        Returns:
            Fused and ranked results
        """
        if self.strategy == "weighted" and self.weights:
            # Apply weights in order of retrievers
            retriever_order = ["bm25", "vector", "graph"]
            weights = [
                self.weights.get(r, 1.0 / len(retriever_order))
                for r in retriever_order[: len(result_lists)]
            ]
            return weighted_fusion(result_lists, weights=weights, top_k=top_k)
        else:
            # Default to RRF
            return reciprocal_rank_fusion(result_lists, top_k=top_k)
