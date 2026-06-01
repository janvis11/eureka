"""Unified hybrid retriever combining all retrieval strategies."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.services.retrieval.query_planner import QueryPlanner, QueryIntent
from app.services.retrieval.bm25_retriever import BM25Retriever
from app.services.retrieval.vector_retriever import VectorRetriever
from app.services.retrieval.graph_retriever import GraphRetriever
from app.services.retrieval.fusion import reciprocal_rank_fusion
from app.services.retrieval.reranker import LLMReranker, quick_rerank
from app.services.retrieval.evidence_pack import EvidencePack, EvidenceItem, build_evidence_pack

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Hybrid retriever combining BM25, vector, and graph retrieval."""

    def __init__(
        self,
        bm25: Optional[BM25Retriever] = None,
        vector: Optional[VectorRetriever] = None,
        graph: Optional[GraphRetriever] = None,
        use_reranker: bool = False,
    ):
        """Initialize hybrid retriever.

        Args:
            bm25: BM25 retriever instance
            vector: Vector retriever instance
            graph: Graph retriever instance
            use_reranker: Whether to use LLM reranker
        """
        self.bm25 = bm25 or BM25Retriever()
        self.vector = vector or VectorRetriever()
        self.graph = graph or GraphRetriever()
        self.planner = QueryPlanner()
        self.reranker = LLMReranker() if use_reranker else None
        self._use_reranker = use_reranker

    def add_documents(
        self,
        documents: List[Dict[str, Any]],
        use_bm25: bool = True,
        use_vector: bool = True,
    ) -> Dict[str, int]:
        """Add documents to retrievers.

        Args:
            documents: List of dicts with 'text' and 'metadata'
            use_bm25: Whether to add to BM25 index
            use_vector: Whether to add to vector index

        Returns:
            Count of documents added to each index
        """
        counts = {}

        if use_bm25:
            for doc in documents:
                doc_id = doc.get("id", doc.get("metadata", {}).get("chunk_id", f"doc_{len(self.bm25.documents)}"))
                self.bm25.add_document(doc_id, doc.get("text", ""), doc.get("metadata"))
            counts["bm25"] = len(documents)

        if use_vector:
            added = self.vector.add_documents(documents)
            counts["vector"] = added

        return counts

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        use_graph: bool = True,
    ) -> EvidencePack:
        """Retrieve evidence for a query.

        Args:
            query: Query text
            top_k: Number of results
            use_graph: Whether to use graph retrieval

        Returns:
            EvidencePack with organized evidence
        """
        # Plan retrieval
        plan = self.planner.plan(query)
        logger.info(f"Query plan: intent={plan.intent}, retrievers={plan.retrievers}")

        # Run retrievers
        result_lists = []

        # BM25 retrieval
        if "bm25" in plan.retrievers:
            bm25_results = self.bm25.search(query, top_k=top_k)
            if bm25_results:
                result_lists.append(bm25_results)

        # Vector retrieval
        if "vector" in plan.retrievers:
            vector_results = self.vector.search(query, top_k=top_k)
            if vector_results:
                result_lists.append(vector_results)

        # Graph retrieval
        if use_graph and "graph" in plan.retrievers:
            graph_results = []
            for entity in plan.entities:
                entity_results = await self.graph.retrieve_by_entity(entity, hops=2, top_k=top_k // 2)
                graph_results.extend(entity_results)
            if graph_results:
                result_lists.append(graph_results)

        # Fuse results
        if not result_lists:
            return EvidencePack(query=query, intent=plan.intent.value)

        fused = reciprocal_rank_fusion(result_lists, top_k=top_k * 2)

        # Rerank if enabled
        if self._use_reranker and len(fused) > 3:
            texts = [r.get("text", "") for r in fused]
            reranked = await self.reranker.rerank(query, texts, top_k=top_k)
            # Merge rerank scores back into original results
            rerank_map = {r.get("text", ""): r for r in reranked}
            for r in fused:
                if r.get("text", "") in rerank_map:
                    r["rerank_score"] = rerank_map[r["text"]].get("rerank_score", 0)

        # Sort by final score
        fused.sort(key=lambda x: x.get("rerank_score", x.get("fusion_score", 0)), reverse=True)
        fused = fused[:top_k]

        # Get graph paths if needed
        graph_paths = []
        if plan.needs_graph_paths and plan.entities:
            for i, entity in enumerate(plan.entities[:-1]):
                next_entity = plan.entities[i + 1] if i + 1 < len(plan.entities) else None
                if next_entity:
                    paths = await self.graph.find_bridge_paths(entity, next_entity)
                    graph_paths.extend(paths)

        # Get counter-evidence if needed
        counter_evidence = []
        if plan.needs_counter_evidence and plan.entities:
            for entity in plan.entities:
                contradictions = await self.graph.find_contradictions(entity)
                for c in contradictions[:2]:
                    counter_evidence.append({
                        "text": c.get("claim_b_text", ""),
                        "score": c.get("contradiction_score", 0),
                        "doc_id": c.get("claim_b_id", ""),
                    })

        # Build evidence pack
        evidence_pack = await build_evidence_pack(
            query=query,
            plan=plan,
            retrieval_results=fused,
            graph_paths=graph_paths,
            counter_evidence=counter_evidence,
        )

        return evidence_pack

    async def search(
        self,
        query: str,
        top_k: int = 10,
        simple: bool = True,
    ) -> List[Dict[str, Any]]:
        """Simple search returning flat results.

        Args:
            query: Query text
            top_k: Number of results
            simple: If True, return simple results without evidence pack

        Returns:
            List of results
        """
        if simple:
            # Quick search without full evidence pack
            bm25_results = self.bm25.search(query, top_k=top_k)
            vector_results = self.vector.search(query, top_k=top_k)

            # Combine and deduplicate
            all_results = []
            seen = set()
            for r in bm25_results + vector_results:
                key = r.get("text", "")[:50]
                if key not in seen:
                    seen.add(key)
                    all_results.append(r)

            all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
            return all_results[:top_k]

        # Full evidence pack
        pack = await self.retrieve(query, top_k=top_k)
        return pack.to_dict()["items"]

    def get_stats(self) -> Dict[str, Any]:
        """Get retriever statistics."""
        return {
            "bm25": self.bm25.get_stats(),
            "vector": self.vector.get_stats(),
            "graph_connected": self.graph._connected if hasattr(self.graph, "_connected") else False,
        }
