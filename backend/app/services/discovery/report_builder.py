"""Report builder for discovery results."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ReportBuilder:
    """Builds structured discovery reports."""

    def __init__(self):
        """Initialize report builder."""
        pass

    def build_full_report(
        self,
        query: str,
        evidence_items: List[Dict[str, Any]],
        contradictions: List[Dict[str, Any]],
        gaps: List[Dict[str, Any]],
        hypotheses: List[Dict[str, Any]],
        trends: Optional[List[Dict[str, Any]]] = None,
        graph_stats: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build a complete discovery report.

        Args:
            query: Original query
            evidence_items: Retrieved evidence
            contradictions: Detected contradictions
            gaps: Identified gaps
            hypotheses: Generated hypotheses
            trends: Optional trending entities
            graph_stats: Optional graph statistics

        Returns:
            Structured report dictionary
        """
        return {
            "report_id": self._generate_report_id(),
            "generated_at": datetime.utcnow().isoformat(),
            "query": query,
            "summary": self._build_summary(
                evidence_items, contradictions, gaps, hypotheses, trends
            ),
            "evidence": {
                "items": evidence_items[:20],
                "total_count": len(evidence_items),
                "counter_evidence_count": sum(
                    1 for e in evidence_items
                    if e.get("evidence_type") == "counter"
                ),
            },
            "contradictions": contradictions[:10],
            "gaps": gaps[:15],
            "hypotheses": hypotheses[:10],
            "trends": trends[:10] if trends else [],
            "graph_stats": graph_stats or {},
            "next_actions": self._suggest_next_actions(
                contradictions, gaps, hypotheses
            ),
        }

    def _build_summary(
        self,
        evidence: List[Dict],
        contradictions: List[Dict],
        gaps: List[Dict],
        hypotheses: List[Dict],
        trends: Optional[List[Dict]],
    ) -> Dict[str, Any]:
        """Build executive summary."""
        return {
            "evidence_found": len(evidence),
            "contradictions_detected": len(contradictions),
            "gaps_identified": len(gaps),
            "hypotheses_generated": len(hypotheses),
            "trends_identified": len(trends) if trends else 0,
            "top_hypothesis": hypotheses[0] if hypotheses else None,
            "key_contradiction": contradictions[0] if contradictions else None,
            "most_critical_gap": gaps[0] if gaps else None,
        }

    def _suggest_next_actions(
        self,
        contradictions: List[Dict],
        gaps: List[Dict],
        hypotheses: List[Dict],
    ) -> List[Dict[str, str]]:
        """Suggest next research actions."""
        actions = []

        if contradictions:
            actions.append({
                "type": "resolve_contradiction",
                "priority": "high",
                "description": f"Resolve contradiction about: {contradictions[0].get('entity', 'unknown')}",
                "action": "Gather additional evidence to reconcile conflicting claims",
            })

        if gaps:
            actions.append({
                "type": "address_gap",
                "priority": "high",
                "description": f"Address gap: {gaps[0].get('description', 'unknown')[:100]}",
                "action": "Design study to fill identified research gap",
            })

        if hypotheses:
            top_hyp = hypotheses[0]
            actions.append({
                "type": "validate_hypothesis",
                "priority": "medium",
                "description": f"Validate: {top_hyp.get('hypothesis', 'unknown')[:100]}",
                "action": "Design experiment to test top hypothesis",
            })

        return actions

    def _generate_report_id(self) -> str:
        """Generate a unique report ID."""
        import hashlib
        timestamp = datetime.utcnow().isoformat()
        return hashlib.sha256(timestamp.encode()).hexdigest()[:16]

    def build_brief_summary(
        self,
        report: Dict[str, Any],
    ) -> str:
        """Build a brief text summary of a report.

        Args:
            report: Full report dictionary

        Returns:
            Brief text summary
        """
        lines = []

        summary = report.get("summary", {})
        lines.append(f"Analysis of: {report.get('query', 'query')}")
        lines.append("")

        lines.append(f"- Evidence items: {summary.get('evidence_found', 0)}")
        lines.append(f"- Contradictions: {summary.get('contradictions_detected', 0)}")
        lines.append(f"- Research gaps: {summary.get('gaps_identified', 0)}")
        lines.append(f"- Hypotheses: {summary.get('hypotheses_generated', 0)}")
        lines.append("")

        top_hyp = summary.get("top_hypothesis")
        if top_hyp:
            lines.append(f"Top hypothesis: {top_hyp.get('hypothesis', 'N/A')}")

        return "\n".join(lines)

    def to_markdown(
        self,
        report: Dict[str, Any],
    ) -> str:
        """Convert report to markdown format.

        Args:
            report: Full report dictionary

        Returns:
            Markdown formatted report
        """
        lines = []

        lines.append(f"# Discovery Report")
        lines.append(f"**Generated:** {report.get('generated_at', 'Unknown')}")
        lines.append(f"**Query:** {report.get('query', 'N/A')}")
        lines.append("")

        # Summary
        summary = report.get("summary", {})
        lines.append("## Summary")
        lines.append(f"- Evidence: {summary.get('evidence_found', 0)} items")
        lines.append(f"- Contradictions: {summary.get('contradictions_detected', 0)}")
        lines.append(f"- Gaps: {summary.get('gaps_identified', 0)}")
        lines.append(f"- Hypotheses: {summary.get('hypotheses_generated', 0)}")
        lines.append("")

        # Top hypotheses
        hypotheses = report.get("hypotheses", [])
        if hypotheses:
            lines.append("## Top Hypotheses")
            for i, hyp in enumerate(hypotheses[:5], 1):
                lines.append(f"### {i}. {hyp.get('hypothesis', 'N/A')}")
                lines.append(f"**Why it matters:** {hyp.get('why_it_matters', 'N/A')}")
                scores = hyp.get("scores", {})
                lines.append(f"**Overall score:** {scores.get('overall', 0):.2f}")
                lines.append("")

        # Contradictions
        contradictions = report.get("contradictions", [])
        if contradictions:
            lines.append("## Contradictions")
            for i, c in enumerate(contradictions[:5], 1):
                lines.append(f"{i}. **{c.get('entity', 'Unknown')}**")
                lines.append(f"   - {c.get('claim_a_text', '')[:100]}...")
                lines.append(f"   - vs {c.get('claim_b_text', '')[:100]}...")
            lines.append("")

        # Gaps
        gaps = report.get("gaps", [])
        if gaps:
            lines.append("## Research Gaps")
            for i, gap in enumerate(gaps[:5], 1):
                lines.append(f"{i}. {gap.get('description', 'N/A')}")
            lines.append("")

        # Next actions
        actions = report.get("next_actions", [])
        if actions:
            lines.append("## Suggested Next Actions")
            for action in actions:
                lines.append(f"- **{action.get('type', 'Unknown')}**: {action.get('description', '')}")
            lines.append("")

        return "\n".join(lines)
