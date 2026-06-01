"""
Enhanced Discovery Engine using provider-agnostic ModelGateway.

Pipeline:
1. Upload papers → Process → Store in RAG
2. RAG Chat: Query papers using semantic search + LLM
3. Discovery: Use ModelGateway + multi-agent orchestration to analyze uploaded documents for:
   - Research gaps (and ranked gaps)
   - Hypothesis generation + validity checking
   - Trend detection
   - Contradiction detection + contradiction graph
   - Hidden bridge discovery (unseen connections)
   - Experiment suggestions
   - Publishable research intelligence report
"""

from typing import List, Dict, Any, Optional
from app.config import get_settings
from app.services.model_gateway.base import ChatMessage, GenerationRequest
from datetime import datetime
import logging
import json
import re

from app.services.science_agents import ScienceAgentOrchestrator
from app.services.contradiction_graph import ContradictionGraphBuilder
from app.services.bridge_discovery import HiddenBridgeDiscovery

logger = logging.getLogger(__name__)


class DiscoveryEngine:
    """Enhanced DiscoveryEngine using ModelGateway + multi-agent orchestration."""

    def __init__(self, rag_engine, keyword_extractor, gateway=None):
        self.settings = get_settings()
        self.rag_engine = rag_engine
        self.keyword_extractor = keyword_extractor

        # Gateway shared instance
        if gateway is not None:
            self.gateway = gateway
        else:
            from app.services.shared import get_gateway
            self.gateway = get_gateway()

        # Initialize multi-agent orchestrator + new analysis services
        self.agent_orchestrator = ScienceAgentOrchestrator(self.gateway, self.keyword_extractor)
        self.contradiction_graph_builder = ContradictionGraphBuilder()
        self.bridge_discovery = HiddenBridgeDiscovery(self.gateway)

    # -----------------------------------------------------------------------
    # CORE GENERATION (via gateway)
    # -----------------------------------------------------------------------
    async def _generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        try:
            result = await self.gateway.generate(
                GenerationRequest(
                    messages=[ChatMessage(role="user", content=prompt)],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            )
            return result.text
        except Exception as e:
            logger.error(f"Generation error: {e}")
            return ""

    def _extract_json(self, text: str) -> dict:
        """Extract JSON object from an LLM response safely."""
        try:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            return {}
        return {}

    # -----------------------------------------------------------------------
    # EXISTING FEATURES (KEEP YOUR ORIGINAL LOGIC BUT CLEANER)
    # -----------------------------------------------------------------------
    async def analyze_research_gaps(self, documents_texts: List[str], top_k: int = 15) -> List[Dict[str, Any]]:
        """Identify research gaps using LLM generation + fallback keyword-based."""
        if not documents_texts:
            return []

        try:
            combined_text = "\n\n".join(documents_texts[:5])[:10000]

            prompt = f"""
Analyze the following research documents and identify research gaps.

Documents:
{combined_text}

Identify 5-10 research gaps. Output JSON:
{{
  "gaps": [
    {{
      "title": "...",
      "description": "...",
      "type": "methodological|theoretical|empirical|application",
      "impact": "high|medium|low",
      "confidence": 0.0-1.0
    }}
  ]
}}
"""
            response = await self._generate(prompt, max_tokens=1024)
            parsed = self._extract_json(response)
            gaps = parsed.get("gaps", [])

            if not gaps:
                logger.info("LLM gaps failed → fallback keyword gap detection")
                gap_analysis = await self.keyword_extractor.detect_gaps(documents_texts)
                gaps = [
                    {
                        "title": f"Missing {gap} coverage",
                        "description": f"Research documents lack comprehensive coverage of {gap}.",
                        "type": "methodological",
                        "impact": "medium",
                        "confidence": 0.6
                    }
                    for gap in gap_analysis.get("gaps", [])[:top_k]
                ]

            normalized = []
            for i, gap in enumerate(gaps[:top_k]):
                normalized.append({
                    "id": f"gap-{i+1}",
                    "title": gap.get("title", f"Research Gap {i+1}"),
                    "description": gap.get("description", ""),
                    "type": gap.get("type", "methodological"),
                    "impact": gap.get("impact", "medium").lower(),
                    "confidence": float(gap.get("confidence", 0.7)),
                })

            return normalized

        except Exception as e:
            logger.error(f"Gap analysis error: {e}")
            return []

    async def generate_hypotheses(self, gaps: List[Dict[str, Any]], documents_texts: List[str], max_hypotheses: int = 10) -> List[Dict[str, Any]]:
        """Generate hypotheses for top gaps."""
        if not gaps:
            return []

        hypotheses = []
        context = "\n\n".join(documents_texts[:3])[:5000] if documents_texts else ""

        for gap in gaps[:5]:
            prompt = f"""
Generate one testable research hypothesis for this gap.

Gap Title: {gap.get("title")}
Gap Description: {gap.get("description")}

Paper Context:
{context}

Output JSON:
{{
  "hypothesis": "...",
  "rationale": "...",
  "evidence": ["supporting evidence item"],
  "counter_evidence": ["missing evidence or possible contradiction"],
  "methodology": "...",
  "validation_plan": "Concrete validation plan",
  "expected_impact": "...",
  "novelty": "What makes this new",
  "feasibility": "Why this can be tested",
  "falsifiability": "What result would disprove it",
  "novelty_score": 0.0-1.0,
  "feasibility_score": 0.0-1.0,
  "falsifiability_score": 0.0-1.0,
  "confidence": 0.0-1.0
}}
"""
            response = await self._generate(prompt, max_tokens=700)
            parsed = self._extract_json(response)

            if parsed.get("hypothesis"):
                novelty_score = float(parsed.get("novelty_score", parsed.get("confidence", 0.65)))
                feasibility_score = float(parsed.get("feasibility_score", 0.7))
                falsifiability_score = float(parsed.get("falsifiability_score", 0.8))
                hypotheses.append({
                    "text": parsed.get("hypothesis", ""),
                    "rationale": parsed.get("rationale", ""),
                    "evidence": parsed.get("evidence", []),
                    "counter_evidence": parsed.get("counter_evidence", []),
                    "methodology": parsed.get("methodology", ""),
                    "validation_plan": parsed.get("validation_plan", parsed.get("methodology", "")),
                    "expected_impact": parsed.get("expected_impact", ""),
                    "novelty": parsed.get("novelty", ""),
                    "feasibility": parsed.get("feasibility", ""),
                    "falsifiability": parsed.get("falsifiability", ""),
                    "novelty_score": novelty_score,
                    "feasibility_score": feasibility_score,
                    "falsifiability_score": falsifiability_score,
                    "confidence": float(parsed.get("confidence", (novelty_score + feasibility_score + falsifiability_score) / 3)),
                    "gap_reference": gap.get("title", ""),
                    "status": "proposed"
                })

        return hypotheses[:max_hypotheses]

    async def detect_trends(self, documents_texts: List[str]) -> List[Dict[str, Any]]:
        """Detect research trends."""
        if not documents_texts:
            return []

        combined_text = "\n\n".join(documents_texts[:5])[:8000]

        prompt = f"""
Analyze these papers and extract trends. Output JSON:

{{
  "trends": [
    {{
      "title": "...",
      "description": "...",
      "velocity": "Rising|Emerging|Exploding|Stable",
      "trend_score": 0.0-1.0
    }}
  ]
}}

Papers:
{combined_text}
"""
        response = await self._generate(prompt, max_tokens=1024)
        parsed = self._extract_json(response)
        trends = parsed.get("trends", [])

        normalized = []
        for t in trends[:15]:
            normalized.append({
                "title": t.get("title", ""),
                "description": t.get("description", ""),
                "velocity": t.get("velocity", "Emerging"),
                "trend_score": float(t.get("trend_score", 0.7))
            })

        normalized.sort(key=lambda x: x["trend_score"], reverse=True)
        return normalized

    async def detect_contradictions(self, documents_texts: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Prompt-based contradiction detection kept for compatibility.
        """
        if not documents_texts or len(documents_texts) < 2:
            return []

        contradictions = []
        for i in range(min(len(documents_texts), 5)):
            for j in range(i + 1, min(len(documents_texts), 5)):
                doc1 = documents_texts[i][:1500]
                doc2 = documents_texts[j][:1500]

                prompt = f"""
Do these two documents contradict? Output JSON.

Doc 1:
{doc1}

Doc 2:
{doc2}

JSON:
{{
  "has_contradiction": true|false,
  "title": "...",
  "description": "...",
  "confidence": 0.0-1.0,
  "impact": "high|medium|low"
}}
"""
                response = await self._generate(prompt, max_tokens=512)
                parsed = self._extract_json(response)

                if parsed.get("has_contradiction"):
                    contradictions.append({
                        "title": parsed.get("title", "Contradiction found"),
                        "description": parsed.get("description", ""),
                        "impact": parsed.get("impact", "medium"),
                        "confidence": float(parsed.get("confidence", 0.7)),
                        "document_pairs": [i, j]
                    })

                if len(contradictions) >= limit:
                    break
            if len(contradictions) >= limit:
                break

        return contradictions

    # -----------------------------------------------------------------------
    # FULL DISCOVERY PIPELINE
    # -----------------------------------------------------------------------
    async def run_full_discovery(self, documents_texts: List[str]) -> Dict[str, Any]:
        """
        Run full enhanced discovery:
        - gaps
        - ranked gaps
        - hypotheses
        - hypothesis validation
        - experiment suggestions
        - contradictions
        - contradiction graph (NLI)
        - hidden bridge discovery
        - trends
        - research intelligence report
        """
        logger.info("Starting FULL discovery pipeline...")

        try:
            # Step 1: gaps
            gaps = await self.analyze_research_gaps(documents_texts, top_k=self.settings.MAX_GAPS)

            # Step 2: gap ranking (multi-agent)
            ranked_gaps = self.agent_orchestrator.gap_ranking_agent(gaps)

            # Step 3: hypotheses
            hypotheses = await self.generate_hypotheses(gaps, documents_texts, self.settings.MAX_HYPOTHESES_PER_RUN)

            # Step 4: hypothesis validity + experiment generation
            validated_hypotheses = []
            experiments = []

            evidence = "\n\n".join(documents_texts[:2])[:6000] if documents_texts else ""
            for h in hypotheses[:5]:
                validation = self.agent_orchestrator.hypothesis_validator_agent(h["text"], evidence)
                h["validation"] = validation
                validated_hypotheses.append(h)

                if validation.get("overall_score", 0) > 0.6:
                    exp = self.agent_orchestrator.experiment_designer_agent(h["text"])
                    experiments.append(exp)

            # Step 5: contradictions (prompt-based)
            contradictions = await self.detect_contradictions(documents_texts, limit=10)

            # Step 6: contradiction graph (NLI model)
            claims = []
            for doc in documents_texts[:4]:
                summary = self.agent_orchestrator.summarizer_agent(doc)
                claims.extend(summary.get("key_results", []))

            contradiction_graph = self.contradiction_graph_builder.build_graph(claims[:12]) if claims else {"nodes": [], "edges": []}

            # Step 7: hidden bridge discovery
            bridges = await self.bridge_discovery.discover_bridges(documents_texts[:8], top_k=8) if documents_texts else []

            # Step 8: trends
            trends = await self.detect_trends(documents_texts)

            # Step 9: final research intelligence report
            bundle = {
                "ranked_gaps": ranked_gaps,
                "validated_hypotheses": validated_hypotheses,
                "experiments": experiments,
                "contradiction_graph": contradiction_graph,
                "hidden_bridges": bridges,
                "trends": trends,
            }
            report = self.agent_orchestrator.report_agent(bundle)

            return {
                "gaps": gaps,
                "ranked_gaps": ranked_gaps,
                "hypotheses": hypotheses,
                "validated_hypotheses": validated_hypotheses,
                "experiments": experiments,
                "contradictions": contradictions,
                "contradiction_graph": contradiction_graph,
                "bridges": bridges,
                "trends": trends,
                "report": report,
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "documents_analyzed": len(documents_texts),
                    "gaps_found": len(gaps),
                    "ranked_gaps": len(ranked_gaps) if ranked_gaps else 0,
                    "hypotheses_generated": len(hypotheses),
                    "hypotheses_validated": len(validated_hypotheses),
                    "experiments_suggested": len(experiments),
                    "contradictions_detected": len(contradictions),
                    "claims_in_graph": len(contradiction_graph.get("nodes", [])),
                    "bridges_found": len(bridges),
                    "trends_identified": len(trends),
                }
            }

        except Exception as e:
            logger.error(f"Discovery pipeline failed: {e}")

            return {
                "gaps": [],
                "ranked_gaps": [],
                "hypotheses": [],
                "validated_hypotheses": [],
                "experiments": [],
                "contradictions": [],
                "contradiction_graph": {"nodes": [], "edges": []},
                "bridges": [],
                "trends": [],
                "report": "",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "documents_analyzed": len(documents_texts) if documents_texts else 0,
                    "gaps_found": 0,
                    "ranked_gaps": 0,
                    "hypotheses_generated": 0,
                    "hypotheses_validated": 0,
                    "experiments_suggested": 0,
                    "contradictions_detected": 0,
                    "claims_in_graph": 0,
                    "bridges_found": 0,
                    "trends_identified": 0,
                }
            }
