"""
Multi-agent scientific discovery system.

This module defines:
- Summarizer Agent
- Gap Ranking Agent
- Contradiction Agent
- Hypothesis Validator Agent
- Experiment Designer Agent
- Report Agent

Each agent uses HuggingFace generation + embeddings.
"""

from typing import Dict, Any, List
import json
import re
import logging

logger = logging.getLogger(__name__)


class ScienceAgentOrchestrator:
    def __init__(self, hf_client, keyword_extractor):
        self.hf_client = hf_client
        self.keyword_extractor = keyword_extractor

    def _json_extract(self, text: str) -> dict:
        """Extract JSON from model response safely."""
        try:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            return {}
        return {}

    def summarizer_agent(self, doc_text: str) -> Dict[str, Any]:
        prompt = f"""
Summarize the following research paper into a structured format.

Paper:
{doc_text[:4000]}

Return JSON:
{{
 "title": "...",
 "core_problem": "...",
 "method": "...",
 "key_results": ["...","..."],
 "limitations": ["...","..."],
 "future_work": ["...","..."]
}}
"""
        response = self.hf_client.generate(prompt, max_length=700)
        return self._json_extract(response)

    def gap_ranking_agent(self, gaps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        prompt = f"""
Rank these research gaps based on:
- novelty
- potential impact
- feasibility
- evidence strength

Gaps:
{json.dumps(gaps[:15], indent=2)}

Return JSON:
{{
  "ranked_gaps":[
    {{
      "title":"...",
      "rank":1,
      "novelty_score":0.0-1.0,
      "impact_score":0.0-1.0,
      "feasibility_score":0.0-1.0,
      "final_score":0.0-1.0,
      "reasoning":"..."
    }}
  ]
}}
"""
        response = self.hf_client.generate(prompt, max_length=800)
        parsed = self._json_extract(response)
        return parsed.get("ranked_gaps", gaps)

    def hypothesis_validator_agent(self, hypothesis: str, evidence: str) -> Dict[str, Any]:
        prompt = f"""
Validate the scientific hypothesis using evidence.

Hypothesis:
{hypothesis}

Evidence from papers:
{evidence[:4000]}

Evaluate:
- testability
- novelty
- consistency with evidence
- feasibility

Return JSON:
{{
  "valid": true|false,
  "testability_score": 0.0-1.0,
  "novelty_score": 0.0-1.0,
  "evidence_support_score": 0.0-1.0,
  "feasibility_score": 0.0-1.0,
  "issues": ["...","..."],
  "suggested_fix": "...",
  "overall_score": 0.0-1.0
}}
"""
        response = self.hf_client.generate(prompt, max_length=700)
        return self._json_extract(response)

    def experiment_designer_agent(self, hypothesis: str) -> Dict[str, Any]:
        prompt = f"""
Design experiments for this hypothesis.

Hypothesis:
{hypothesis}

Return JSON:
{{
  "experiments":[
    {{
      "experiment_title":"...",
      "goal":"...",
      "methodology":"...",
      "data_required":"...",
      "metrics":"...",
      "expected_outcome":"..."
    }}
  ]
}}
"""
        response = self.hf_client.generate(prompt, max_length=700)
        parsed = self._json_extract(response)
        return parsed

    def report_agent(self, discovery_bundle: Dict[str, Any]) -> str:
        prompt = f"""
Generate a publishable research intelligence report from this discovery bundle.

Bundle:
{json.dumps(discovery_bundle, indent=2)}

Write as a structured report:
1. Executive Summary
2. Trends
3. Contradictions
4. Ranked Gaps
5. Proposed Hypotheses
6. Experiments
7. Suggested Future Work

Write cleanly and concisely.
"""
        return self.hf_client.generate(prompt, max_length=1200)
