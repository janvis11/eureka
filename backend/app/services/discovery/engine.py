"""Unified discovery engine coordinating all agents."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.services.discovery.claim_extractor import ClaimExtractor
from app.services.discovery.relation_extractor import RelationExtractor
from app.services.discovery.contradiction_miner import ContradictionMiner
from app.services.discovery.contradiction_verifier import ContradictionVerifier
from app.services.discovery.bridge_discovery import BridgeFinder
from app.services.discovery.gap_detector import GapDetector
from app.services.discovery.hypothesis_generator import HypothesisGenerator
from app.services.discovery.hypothesis_validator import HypothesisValidator
from app.services.discovery.experiment_designer import ExperimentDesigner
from app.services.discovery.trend_radar import TrendRadar
from app.services.discovery.report_builder import ReportBuilder
from app.services.discovery.heuristic_priors import rank_hypotheses
from app.services.graph.repository import GraphRepository
from app.services.graph.neo4j_client import get_neo4j_client
from app.services.retrieval.hybrid_retriever import HybridRetriever

logger = logging.getLogger(__name__)


class DiscoveryEngine:
    """Main discovery engine coordinating all agents."""

    def __init__(
        self,
        hybrid_retriever: Optional[HybridRetriever] = None,
        graph_repository: Optional[GraphRepository] = None,
    ):
        """Initialize discovery engine.

        Args:
            hybrid_retriever: Optional hybrid retriever
            graph_repository: Optional graph repository
        """
        self.retriever = hybrid_retriever or HybridRetriever()
        self.graph = graph_repository or GraphRepository(get_neo4j_client())

        # Initialize agents
        self.claim_extractor = ClaimExtractor()
        self.relation_extractor = RelationExtractor()
        self.contradiction_miner = ContradictionMiner()
        self.contradiction_verifier = ContradictionVerifier()
        self.bridge_finder = BridgeFinder(self.graph)
        self.gap_detector = GapDetector()
        self.hypothesis_generator = HypothesisGenerator()
        self.hypothesis_validator = HypothesisValidator()
        self.experiment_designer = ExperimentDesigner()
        self.trend_radar = TrendRadar(self.graph)
        self.report_builder = ReportBuilder()

        # Cache for extracted data
        self._extracted_claims: List[Dict] = []
        self._extracted_relations: List[Dict] = []

    async def run_full_discovery(
        self,
        query: str,
        documents: Optional[List[str]] = None,
        top_k: int = 15,
        generate_hypotheses: bool = True,
    ) -> Dict[str, Any]:
        """Run full discovery pipeline.

        Args:
            query: Research query
            documents: Optional list of document texts to analyze
            top_k: Number of evidence items to retrieve
            generate_hypotheses: Whether to generate hypotheses

        Returns:
            Complete discovery report
        """
        logger.info(f"Starting discovery for query: {query[:100]}...")

        # Step 1: Retrieve evidence
        evidence_pack = await self.retriever.retrieve(query, top_k=top_k)
        evidence_items = evidence_pack.to_dict()["items"]

        # Step 2: Extract claims from evidence
        claims = await self._extract_claims_from_evidence(evidence_items)

        # Step 3: Find and verify contradictions (candidate miner -> LLM filter)
        contradiction_result = await self._mine_and_verify_contradictions(claims)
        contradictions = contradiction_result["contradictions"]

        # Step 4: Detect gaps from claims
        gaps = self.gap_detector.find_gaps_from_claims(claims)

        # Step 5: Generate hypotheses if requested
        hypotheses = []
        if generate_hypotheses:
            hypotheses = await self.hypothesis_generator.generate(
                evidence_items=evidence_items,
                contradictions=contradictions,
                gaps=gaps,
            )
            # Rank hypotheses
            hypotheses = rank_hypotheses(hypotheses, top_k=10)

        # Step 6: Get trends
        trends = await self.trend_radar.find_trending_entities(days=365, limit=10)

        # Step 7: Build report
        report = self.report_builder.build_full_report(
            query=query,
            evidence_items=evidence_items,
            contradictions=contradictions,
            gaps=gaps,
            hypotheses=hypotheses,
            trends=trends,
        )
        report["contradiction_verification"] = contradiction_result["stats"]
        report["context_differences"] = contradiction_result["context_differences"][:10]

        logger.info(
            "Discovery complete: %d hypotheses, %d confirmed contradictions "
            "(%d candidates, %d were context differences, not contradictions)",
            len(hypotheses), len(contradictions),
            contradiction_result["stats"]["candidates"],
            contradiction_result["stats"]["context_differences"],
        )
        return report

    async def _mine_and_verify_contradictions(
        self, claims: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Two-stage contradiction detection: the keyword miner is a cheap,
        high-recall candidate generator; the LLM verifier is the high-precision
        filter that tells genuine contradictions apart from claims that only
        differ by context (population, dataset, dosage, timeframe, ...)."""
        candidates = self.contradiction_miner.find_contradictions(claims)
        if not candidates:
            return {
                "contradictions": [],
                "context_differences": [],
                "not_related": [],
                "stats": {
                    "candidates": 0,
                    "confirmed_contradictions": 0,
                    "context_differences": 0,
                    "not_related": 0,
                },
            }
        return await self.contradiction_verifier.verify_batch(candidates)

    async def _extract_claims_from_evidence(
        self,
        evidence_items: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Extract claims from evidence items."""
        texts = [e.get("text", "") for e in evidence_items if e.get("text")]

        if not texts:
            return []

        claims = await self.claim_extractor.extract_batch(texts)

        # Store for later use
        self._extracted_claims = claims
        return claims

    async def analyze_documents(
        self,
        documents: List[str],
        chunk_size: int = 2000,
    ) -> Dict[str, Any]:
        """Analyze a list of documents.

        Args:
            documents: List of document texts
            chunk_size: Size of chunks for processing

        Returns:
            Analysis results with claims and relations
        """
        all_claims = []
        all_relations = []

        for i, doc in enumerate(documents):
            logger.info(f"Processing document {i + 1}/{len(documents)}")

            # Chunk document
            chunks = self._chunk_text(doc, chunk_size)

            # Extract claims
            claims = await self.claim_extractor.extract_batch(chunks)
            all_claims.extend(claims)

            # Extract relations
            for chunk in chunks:
                relations = await self.relation_extractor.extract(chunk)
                all_relations.extend(relations)

        # Find and verify contradictions (candidate miner -> LLM filter)
        contradiction_result = await self._mine_and_verify_contradictions(all_claims)

        # Detect gaps
        gaps = self.gap_detector.find_gaps_from_claims(all_claims)

        return {
            "documents_processed": len(documents),
            "claims_extracted": len(all_claims),
            "relations_extracted": len(all_relations),
            "contradictions": contradiction_result["contradictions"],
            "context_differences": contradiction_result["context_differences"],
            "contradiction_verification": contradiction_result["stats"],
            "gaps": self.gap_detector.aggregate_gaps(gaps),
            "claims": all_claims[:50],  # Limit output
        }

    def _chunk_text(self, text: str, size: int, overlap: int = 200) -> List[str]:
        """Chunk text into overlapping segments."""
        chunks = []
        start = 0

        while start < len(text):
            end = start + size
            chunk = text[start:end]

            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk.rfind(".")
                if last_period > size // 2:
                    chunk = chunk[: last_period + 1]
                    end = start + last_period + 1

            chunks.append(chunk.strip())
            start = end - overlap

        return chunks

    async def design_experiments_for_hypotheses(
        self,
        hypotheses: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Design experiments for a list of hypotheses.

        Args:
            hypotheses: List of hypotheses

        Returns:
            List of experiment designs
        """
        designs = []
        for hyp in hypotheses:
            design = await self.experiment_designer.design(
                hypothesis=hyp.get("hypothesis", ""),
                why_it_matters=hyp.get("why_it_matters", ""),
                supporting_evidence=hyp.get("supporting_evidence", []),
            )
            design["hypothesis_id"] = hyp.get("id", hyp.get("hypothesis", "")[:50])
            design["hypothesis_scores"] = hyp.get("scores", {})
            designs.append(design)

        return designs

    async def get_field_landscape(
        self,
        entity_type: Optional[str] = None,
        days: int = 365,
    ) -> Dict[str, Any]:
        """Get landscape overview of a research field.

        Args:
            entity_type: Optional entity type filter
            days: Time window

        Returns:
            Field landscape
        """
        overview = await self.trend_radar.get_field_overview(
            entity_type=entity_type,
            days=days,
        )

        # Add weak signals
        weak_signals = await self.trend_radar.detect_weak_signals(limit=10)
        overview["weak_signals"] = weak_signals

        return overview
