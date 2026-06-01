"""Relation extraction between entities."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from app.services.model_gateway import (
    ChatMessage,
    GenerationRequest,
    create_gateway,
)

logger = logging.getLogger(__name__)


RELATION_EXTRACTION_PROMPT = """Extract relationships between entities from the text.

Valid relationship types:
- improves: A improves/enhances B
- reduces: A reduces/decreases B
- causes: A causes/leads to B
- correlates_with: A correlates with B
- contradicts: A contradicts B
- uses: A uses/employs B
- evaluated_on: A was evaluated on B (dataset/metric)
- limited_by: A is limited by B
- enables: A enables/allows B
- inspired_by: A was inspired by B

Text:
{text}

Entities mentioned: {entities}

Respond ONLY with a JSON array of relationships:
[
  {{
    "subject": "EntityA",
    "predicate": "improves",
    "object": "EntityB",
    "evidence": "quote from text",
    "confidence": 0.9
  }}
]
"""


class RelationExtractor:
    """Extracts typed relationships between entities."""

    VALID_RELATIONS = {
        "improves", "reduces", "causes", "correlates_with",
        "contradicts", "uses", "evaluated_on", "limited_by",
        "enables", "inspired_by",
    }

    def __init__(self, gateway=None):
        """Initialize relation extractor."""
        self._gateway = gateway or create_gateway()

    async def extract(
        self,
        text: str,
        entities: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Extract relationships from text.

        Args:
            text: Text to extract relations from
            entities: Optional list of known entities

        Returns:
            List of extracted relationships
        """
        if len(text) < 50:
            return []

        entity_str = ", ".join(entities) if entities else "auto-detect"

        try:
            result = await self._gateway.generate(
                GenerationRequest(
                    messages=[
                        ChatMessage(
                            role="system",
                            content="Extract entity relationships. Return ONLY valid JSON.",
                        ),
                        ChatMessage(
                            role="user",
                            content=RELATION_EXTRACTION_PROMPT.format(
                                text=text[:4000],
                                entities=entity_str,
                            ),
                        ),
                    ],
                    temperature=0.1,
                    max_tokens=1200,
                    json_mode=True,
                )
            )

            relations = self._parse_relations(result.text)
            return relations

        except Exception as e:
            logger.error(f"Relation extraction failed: {e}")
            return []

    def _parse_relations(self, text: str) -> List[Dict[str, Any]]:
        """Parse LLM output into relations."""
        import json
        import re

        match = re.search(r"\[.*?\]", text, re.DOTALL)
        if not match:
            return []

        try:
            relations = json.loads(match.group())
            if not isinstance(relations, list):
                return []

            parsed = []
            for rel in relations:
                if not isinstance(rel, dict):
                    continue

                predicate = rel.get("predicate", "")
                if predicate not in self.VALID_RELATIONS:
                    continue

                parsed.append({
                    "subject": rel.get("subject", ""),
                    "predicate": predicate,
                    "object": rel.get("object", ""),
                    "evidence": rel.get("evidence", ""),
                    "confidence": float(rel.get("confidence", 0.5)),
                })

            return parsed

        except (json.JSONDecodeError, ValueError):
            return []

    def normalize_entity_key(self, name: str, known_entities: Set[str]) -> Optional[str]:
        """Match entity name to known entity key.

        Args:
            name: Entity name from text
            known_entities: Set of known entity keys

        Returns:
            Matching entity key or None
        """
        name_lower = name.lower()

        # Direct match
        for key in known_entities:
            if name_lower in key.lower() or key.lower() in name_lower:
                return key

        # Try without type suffix
        name_base = name_lower.split(":")[0] if ":" in name_lower else name_lower
        for key in known_entities:
            key_base = key.lower().split(":")[0]
            if name_base == key_base:
                return key

        return None
