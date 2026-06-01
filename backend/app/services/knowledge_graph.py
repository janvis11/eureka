"""
Simplified keyword extraction from documents.
Stores keywords in PostgreSQL, no Neo4j or spaCy needed.
Uses ModelGateway for keyphrase extraction when available.
"""

from typing import List, Dict, Any, Optional
from collections import Counter
import re
import asyncio
from app.config import get_settings
from app.services.model_gateway.base import ChatMessage, GenerationRequest


class KeywordExtractor:
    """Extract and analyze keywords from documents."""

    def __init__(self, gateway: Optional[object] = None):
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which', 'who',
            'when', 'where', 'why', 'how', 'all', 'each', 'every', 'both', 'few',
            'more', 'most', 'some', 'any', 'no', 'nor', 'not', 'as', 'if', 'then'
        }
        if gateway is not None:
            self.gateway = gateway
        else:
            from app.services.shared import get_gateway
            self.gateway = get_gateway()
        self.settings = get_settings()

    def extract_keywords(self, text: str, num_keywords: int = 20) -> List[str]:
        """Extract important keywords using frequency analysis."""
        words = text.lower().split()

        # Filter: remove stop words, short words
        keywords = [
            w.strip('.,;:!?()[]{}') for w in words
            if w.lower() not in self.stop_words
            and len(w) > 3
            and re.match(r'^[a-z0-9\-]+$', w.lower())
        ]

        # Remove duplicates and count
        counter = Counter(keywords)
        return [word for word, _ in counter.most_common(num_keywords)]

    def extract_keyphrases(self, text: str, num_phrases: int = 10) -> List[str]:
        """Extract keyphrases.

        If a gateway is available, use it to extract high-quality keyphrases.
        Otherwise, fall back to a simple capitalized-sequence heuristic.
        """
        # Prefer gateway-based extraction if available
        if self.gateway:
            try:
                prompt = f"Extract the top {num_phrases} keyphrases from the text below. Return a comma-separated list with no explanation.\n\nText:\n" + text[:2000]
                # Use sync execution for backwards compat
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as pool:
                            future = pool.submit(
                                asyncio.run,
                                self.gateway.generate(
                                    GenerationRequest(
                                        messages=[ChatMessage(role="user", content=prompt)],
                                        max_tokens=128,
                                        temperature=0.1,
                                    )
                                )
                            )
                            result = future.result(timeout=30)
                    else:
                        result = loop.run_until_complete(
                            self.gateway.generate(
                                GenerationRequest(
                                    messages=[ChatMessage(role="user", content=prompt)],
                                    max_tokens=128,
                                    temperature=0.1,
                                )
                            )
                        )
                    resp = result.text
                except RuntimeError:
                    # No event loop — run directly
                    result = asyncio.run(
                        self.gateway.generate(
                            GenerationRequest(
                                messages=[ChatMessage(role="user", content=prompt)],
                                max_tokens=128,
                                temperature=0.1,
                            )
                        )
                    )
                    resp = result.text

                if resp:
                    parts = [p.strip() for p in re.split(r'[;,\n]+', resp) if p.strip()]
                    return parts[:num_phrases]
            except Exception:
                # Fall back to heuristic
                pass

        words = text.split()
        phrases = []
        seen = set()

        # Look for capitalized word sequences
        for i in range(len(words) - 1):
            if words[i][0].isupper() and words[i+1][0].isupper():
                phrase = f"{words[i]} {words[i+1]}"
                if phrase not in seen and len(phrase) > 5:
                    phrases.append(phrase)
                    seen.add(phrase)

        return phrases[:num_phrases]

    async def get_document_concepts(self, text: str) -> Dict[str, Any]:
        """Analyze key concepts in a single document."""
        keywords = self.extract_keywords(text, num_keywords=15)
        phrases = self.extract_keyphrases(text, num_phrases=10)

        return {
            "keywords": keywords,
            "phrases": phrases,
            "concept_count": len(set(keywords + phrases))
        }

    async def find_document_overlap(self, texts: List[str]) -> Dict[str, Any]:
        """Find common themes between multiple documents."""
        if len(texts) < 2:
            return {
                "overlap": [],
                "unique_per_doc": [],
                "overlap_score": 0
            }

        # Extract keywords from each
        all_keywords = [set(self.extract_keywords(t)) for t in texts]

        # Find common keywords
        common = set.intersection(*all_keywords) if len(all_keywords) > 1 else set()

        # Find unique per document
        unique = []
        for i, kw_set in enumerate(all_keywords):
            others = set().union(*[all_keywords[j] for j in range(len(all_keywords)) if j != i])
            unique.append(list(kw_set - others))

        overlap_score = len(common) / max(1, len(all_keywords[0]))

        return {
            "overlap": list(common),
            "unique_per_doc": unique,
            "overlap_score": round(overlap_score, 2)
        }

    async def detect_gaps(self, texts: List[str]) -> Dict[str, Any]:
        """Detect potential research gaps based on keyword analysis."""
        if not texts:
            return {"gaps": [], "coverage": 0}

        # Common research elements to look for
        research_elements = {
            'methodology': ['method', 'approach', 'technique', 'experiment', 'framework'],
            'results': ['result', 'finding', 'outcome', 'conclusion', 'evidence'],
            'literature': ['review', 'survey', 'related', 'prior', 'background'],
            'theory': ['theory', 'theoretical', 'model', 'hypothesis', 'principle'],
            'validation': ['test', 'validation', 'verify', 'experiment', 'evaluation'],
            'limitation': ['limitation', 'challenge', 'constraint', 'issue', 'problem']
        }

        all_text = ' '.join(texts).lower()
        covered = []
        missing = []

        for element, keywords in research_elements.items():
            if any(kw in all_text for kw in keywords):
                covered.append(element)
            else:
                missing.append(element)

        coverage = len(covered) / len(research_elements)

        return {
            "covered": covered,
            "missing": missing,
            "coverage_score": round(coverage, 2),
            "gaps": missing
        }

    async def detect_trends(self, texts: List[str]) -> Dict[str, Any]:
        """Detect emerging concepts/trends across documents."""
        if not texts:
            return {"trends": [], "trend_strength": 0}

        # Extract keywords from each document
        keyword_sets = [set(self.extract_keywords(t, num_keywords=10)) for t in texts]

        # Count concept frequency across documents
        concept_freq = Counter()
        for kw_set in keyword_sets:
            for kw in kw_set:
                concept_freq[kw] += 1

        # Concepts appearing in 2+ documents are trends
        trends = [kw for kw, count in concept_freq.most_common(20) if count >= 2]

        trend_strength = len(trends) / max(1, len(set(k for s in keyword_sets for k in s)))

        return {
            "trends": trends,
            "trend_strength": round(trend_strength, 2),
            "trend_count": len(trends)
        }
