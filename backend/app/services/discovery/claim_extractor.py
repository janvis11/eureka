"""Claim extraction from text chunks."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.services.model_gateway import (
    ChatMessage,
    GenerationRequest,
    create_gateway,
)

logger = logging.getLogger(__name__)


CLAIM_EXTRACTION_PROMPT = """Extract all claims from the following text. A claim is a statement of fact, finding, method, limitation, or future work.

For each claim, identify:
- text: The claim in your own words (concise)
- claim_type: One of "finding", "method", "limitation", "comparison", "definition", "future_work"
- entities: Named entities mentioned (methods, datasets, metrics, concepts)
- polarity: "positive" (supports/improves), "negative" (limits/reduces), or "neutral"
- confidence: Your confidence in this extraction (0.0-1.0)
- source_quote: The exact phrase from the text

Text:
{text}

Respond ONLY with a JSON array of claims:
[
  {{
    "text": "...",
    "claim_type": "finding",
    "entities": ["Entity1", "Entity2"],
    "polarity": "positive",
    "confidence": 0.9,
    "source_quote": "exact quote"
  }}
]
"""


class ClaimExtractor:
    """Extracts structured claims from text."""

    def __init__(self, gateway=None):
        """Initialize claim extractor.

        Args:
            gateway: Optional model gateway instance
        """
        self._gateway = gateway or create_gateway()

    async def extract(self, text: str, chunk_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Extract claims from text.

        Args:
            text: Text to extract claims from
            chunk_id: Optional chunk identifier

        Returns:
            List of extracted claims
        """
        if len(text) < 50:
            return []

        try:
            result = await self._gateway.generate(
                GenerationRequest(
                    messages=[
                        ChatMessage(
                            role="system",
                            content="Extract claims from scientific text. Return ONLY valid JSON.",
                        ),
                        ChatMessage(role="user", content=CLAIM_EXTRACTION_PROMPT.format(text=text[:4000])),
                    ],
                    temperature=0.1,
                    max_tokens=1500,
                    json_mode=True,
                )
            )

            claims = self._parse_claims(result.text)

            # Add chunk_id if provided
            if chunk_id:
                for claim in claims:
                    claim["chunk_id"] = chunk_id

            return claims

        except Exception as e:
            logger.error(f"Claim extraction failed: {e}")
            return []

    def _parse_claims(self, text: str) -> List[Dict[str, Any]]:
        """Parse LLM output into claims."""
        import json
        import re

        # Try to extract JSON array
        match = re.search(r"\[.*?\]", text, re.DOTALL)
        if not match:
            return []

        try:
            claims = json.loads(match.group())
            if not isinstance(claims, list):
                return []

            parsed = []
            for claim in claims:
                if not isinstance(claim, dict):
                    continue

                parsed.append({
                    "text": claim.get("text", ""),
                    "claim_type": self._validate_claim_type(claim.get("claim_type", "finding")),
                    "entities": claim.get("entities", []) or [],
                    "polarity": self._validate_polarity(claim.get("polarity", "neutral")),
                    "confidence": float(claim.get("confidence", 0.5)),
                    "source_quote": claim.get("source_quote", ""),
                })

            return parsed

        except (json.JSONDecodeError, ValueError):
            return []

    def _validate_claim_type(self, claim_type: str) -> str:
        """Validate and normalize claim type."""
        valid_types = {"finding", "method", "limitation", "comparison", "definition", "future_work"}
        if claim_type in valid_types:
            return claim_type
        return "finding"  # Default

    def _validate_polarity(self, polarity: str) -> str:
        """Validate and normalize polarity."""
        valid_polarities = {"positive", "negative", "neutral"}
        if polarity in valid_polarities:
            return polarity
        return "neutral"  # Default

    async def extract_batch(
        self,
        texts: List[str],
        chunk_ids: Optional[List[str]] = None,
        concurrency: int = 3,
    ) -> List[Dict[str, Any]]:
        """Extract claims from multiple texts.

        Args:
            texts: List of texts
            chunk_ids: Optional list of chunk IDs
            concurrency: Number of concurrent extractions

        Returns:
            Flattened list of all claims
        """
        import asyncio

        chunk_ids = chunk_ids or [None] * len(texts)

        # Process with concurrency limit
        semaphore = asyncio.Semaphore(concurrency)

        async def extract_with_semaphore(text, chunk_id):
            async with semaphore:
                return await self.extract(text, chunk_id)

        tasks = [
            extract_with_semaphore(text, cid)
            for text, cid in zip(texts, chunk_ids)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results
        all_claims = []
        for result in results:
            if isinstance(result, list):
                all_claims.extend(result)

        return all_claims
