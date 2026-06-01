"""Document-to-graph ingestion pipeline.

Turns uploaded paper chunks into provenance-rich graph primitives:
Document -> Chunk -> Entity -> Claim plus entity relationships. LLM
extractors are used when available, while deterministic text heuristics keep
local development functional without model downloads or provider lock-in.
"""

from __future__ import annotations

import hashlib
import itertools
import logging
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from app.services.discovery.claim_extractor import ClaimExtractor
from app.services.discovery.relation_extractor import RelationExtractor
from app.services.graph.repository import GraphRepository
from app.services.graph.schema import (
    ChunkGraphPayload,
    ClaimPayload,
    DocumentGraphPayload,
    EntityPayload,
)
from app.services.knowledge_graph import KeywordExtractor

logger = logging.getLogger(__name__)


ENTITY_TYPES = {
    "METHOD",
    "DATASET",
    "CONCEPT",
    "METRIC",
    "ORGANIZATION",
    "PERSON",
    "MATERIAL",
    "GENE",
    "DISEASE",
    "TASK",
}


def slugify_entity_name(name: str) -> str:
    """Normalize entity names to stable graph keys."""
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")
    return cleaned[:80] or "unknown"


def infer_entity_type(name: str) -> str:
    """Small domain heuristic for entity typing."""
    lower = name.lower()

    if any(token in lower for token in ("dataset", "corpus", "benchmark", "imagenet", "pubmed")):
        return "DATASET"
    if any(token in lower for token in ("accuracy", "auc", "f1", "precision", "recall", "mae", "rmse")):
        return "METRIC"
    if any(token in lower for token in ("method", "algorithm", "model", "framework", "rag", "transformer", "network")):
        return "METHOD"
    if any(token in lower for token in ("protein", "gene", "crispr", "rna", "dna")):
        return "GENE"
    if any(token in lower for token in ("cancer", "disease", "syndrome", "infection")):
        return "DISEASE"
    if any(token in lower for token in ("polymer", "catalyst", "electrolyte", "alloy", "material")):
        return "MATERIAL"
    if any(token in lower for token in ("classification", "segmentation", "prediction", "retrieval")):
        return "TASK"

    return "CONCEPT"


def normalize_entity_key(name: str, entity_type: Optional[str] = None) -> str:
    """Return a canonical entity key in roadmap format."""
    etype = (entity_type or infer_entity_type(name)).upper()
    if etype not in ENTITY_TYPES:
        etype = "CONCEPT"
    return f"{slugify_entity_name(name)}:{etype}"


class GraphIngestionPipeline:
    """Ingest extracted document text/chunks into Neo4j."""

    def __init__(
        self,
        repository: GraphRepository,
        gateway: Optional[object] = None,
        keyword_extractor: Optional[KeywordExtractor] = None,
        max_claim_chunks: int = 12,
        max_entities_per_chunk: int = 12,
    ):
        self.repository = repository
        self.keyword_extractor = keyword_extractor or KeywordExtractor(gateway=gateway)
        self.claim_extractor = ClaimExtractor(gateway=gateway)
        self.relation_extractor = RelationExtractor(gateway=gateway)
        self.max_claim_chunks = max_claim_chunks
        self.max_entities_per_chunk = max_entities_per_chunk

    async def ingest_document(
        self,
        document_id: str,
        title: str,
        metadata: Dict[str, Any],
        chunks: List[Dict[str, Any]],
        full_text: str,
        source_type: str = "pdf",
    ) -> Dict[str, int]:
        """Persist a processed document as a provenance-rich graph."""
        await self.repository.upsert_document(
            DocumentGraphPayload(
                id=document_id,
                title=title,
                source_type=source_type,
                created_at=datetime.now().isoformat(),
                metadata=metadata or {},
            )
        )

        counts = {
            "documents": 1,
            "chunks": 0,
            "entities": 0,
            "claims": 0,
            "relationships": 0,
        }

        seen_entities: set[str] = set()

        for index, chunk in enumerate(chunks):
            text = (chunk.get("text") or "").strip()
            if not text:
                continue

            chunk_id = f"doc_{document_id}_chunk_{chunk.get('chunk_index', index)}"
            await self.repository.upsert_chunk(
                ChunkGraphPayload(
                    id=chunk_id,
                    document_id=document_id,
                    text=text[:12000],
                    chunk_index=int(chunk.get("chunk_index", index)),
                    token_count=len(text.split()),
                )
            )
            counts["chunks"] += 1

            entity_names = self._extract_candidate_entities(text)
            entity_payloads = self._build_entity_payloads(entity_names)
            entity_keys = [entity.key for entity in entity_payloads]

            for entity in entity_payloads:
                await self.repository.upsert_entity(entity)
                if entity.key not in seen_entities:
                    counts["entities"] += 1
                    seen_entities.add(entity.key)

            if entity_keys:
                await self.repository.link_chunk_to_entities(chunk_id, entity_keys)

            # Co-occurrence edges make hidden bridges traversable even before an
            # LLM relation extractor finds a typed predicate.
            counts["relationships"] += await self._link_co_occurring_entities(
                entity_keys=entity_keys,
                chunk_id=chunk_id,
                evidence=text,
            )

            if index < self.max_claim_chunks:
                claims = await self._extract_claims(text, chunk_id, entity_names)
                for claim in claims:
                    claim_id = self._stable_id("claim", document_id, chunk_id, claim["text"])
                    await self.repository.upsert_claim(
                        ClaimPayload(
                            id=claim_id,
                            text=claim["text"][:1500],
                            claim_type=claim["claim_type"],
                            polarity=claim["polarity"],
                            confidence=float(claim.get("confidence", 0.55)),
                            source_quote=claim.get("source_quote", claim["text"])[:1500],
                            chunk_id=chunk_id,
                        )
                    )
                    counts["claims"] += 1

                    claim_entities = self._build_entity_payloads(claim.get("entities", []) or entity_names[:4])
                    claim_entity_keys = []
                    for entity in claim_entities:
                        await self.repository.upsert_entity(entity)
                        claim_entity_keys.append(entity.key)
                        if entity.key not in seen_entities:
                            counts["entities"] += 1
                            seen_entities.add(entity.key)

                    if claim_entity_keys:
                        await self.repository.link_claim_to_entities(claim_id, claim_entity_keys)

                counts["relationships"] += await self._extract_typed_relations(
                    text=text,
                    chunk_id=chunk_id,
                    entity_names=entity_names,
                )

        logger.info(
            "Graph ingestion complete for document %s: %s",
            document_id,
            counts,
        )
        return counts

    def _extract_candidate_entities(self, text: str) -> List[str]:
        """Extract candidate concepts from the actual paper text."""
        keywords = self.keyword_extractor.extract_keywords(text, num_keywords=10)

        capitalized_phrases = re.findall(
            r"\b(?:[A-Z][A-Za-z0-9\-]+(?:\s+|$)){2,5}",
            text[:5000],
        )

        method_phrases = re.findall(
            r"\b(?:[a-zA-Z0-9\-]+(?:RAG|Net|BERT|GPT|CRISPR|RNA|DNA)[a-zA-Z0-9\-]*)\b",
            text[:5000],
        )

        candidates = [*capitalized_phrases, *method_phrases, *keywords]
        return self._dedupe_entity_names(candidates)[: self.max_entities_per_chunk]

    def _dedupe_entity_names(self, candidates: Iterable[str]) -> List[str]:
        names = []
        seen = set()

        for raw in candidates:
            name = re.sub(r"\s+", " ", raw).strip(" .,:;()[]{}")
            if not (3 <= len(name) <= 90):
                continue
            if name.lower() in self.keyword_extractor.stop_words:
                continue
            key = slugify_entity_name(name)
            if key in seen:
                continue
            seen.add(key)
            names.append(name)

        return names

    def _build_entity_payloads(self, names: Iterable[str]) -> List[EntityPayload]:
        payloads = []
        for name in self._dedupe_entity_names(names):
            entity_type = infer_entity_type(name)
            payloads.append(
                EntityPayload(
                    key=normalize_entity_key(name, entity_type),
                    name=name,
                    type=entity_type,
                    aliases=[],
                    description=None,
                )
            )
        return payloads

    async def _extract_claims(
        self,
        text: str,
        chunk_id: str,
        entity_names: List[str],
    ) -> List[Dict[str, Any]]:
        claims = await self.claim_extractor.extract(text, chunk_id=chunk_id)
        if claims:
            return claims[:6]
        return self._heuristic_claims(text, entity_names)[:4]

    def _heuristic_claims(self, text: str, entity_names: List[str]) -> List[Dict[str, Any]]:
        """Fallback claim extraction grounded in source sentences."""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        claim_markers = (
            "show",
            "shows",
            "found",
            "suggest",
            "demonstrate",
            "improve",
            "reduce",
            "limit",
            "challenge",
            "propose",
            "outperform",
            "increase",
            "decrease",
        )

        claims = []
        for sentence in sentences:
            clean = sentence.strip()
            if len(clean) < 60 or len(clean) > 700:
                continue
            lower = clean.lower()
            if not any(marker in lower for marker in claim_markers):
                continue

            claim_type = "finding"
            polarity = "neutral"
            if any(word in lower for word in ("limit", "challenge", "fail", "decrease", "reduce")):
                claim_type = "limitation"
                polarity = "negative"
            elif any(word in lower for word in ("propose", "method", "framework", "algorithm")):
                claim_type = "method"
                polarity = "positive"
            elif any(word in lower for word in ("improve", "outperform", "increase", "enhance")):
                polarity = "positive"

            sentence_entities = [name for name in entity_names if name.lower() in lower]
            claims.append(
                {
                    "text": clean,
                    "claim_type": claim_type,
                    "entities": sentence_entities or entity_names[:4],
                    "polarity": polarity,
                    "confidence": 0.55,
                    "source_quote": clean,
                }
            )

        return claims

    async def _link_co_occurring_entities(
        self,
        entity_keys: List[str],
        chunk_id: str,
        evidence: str,
    ) -> int:
        if len(entity_keys) < 2:
            return 0

        linked = 0
        unique_keys = list(dict.fromkeys(entity_keys))
        for source_key, target_key in itertools.combinations(unique_keys[:8], 2):
            await self.repository.upsert_entity_relation(
                source_key=source_key,
                target_key=target_key,
                predicate="co_occurs",
                evidence=evidence[:500],
                confidence=0.45,
                chunk_id=chunk_id,
            )
            linked += 1
        return linked

    async def _extract_typed_relations(
        self,
        text: str,
        chunk_id: str,
        entity_names: List[str],
    ) -> int:
        if len(entity_names) < 2:
            return 0

        relations = await self.relation_extractor.extract(text, entity_names)
        linked = 0

        for relation in relations[:10]:
            subject = relation.get("subject", "")
            obj = relation.get("object", "")
            if not subject or not obj:
                continue

            subject_payload = self._build_entity_payloads([subject])
            object_payload = self._build_entity_payloads([obj])
            if not subject_payload or not object_payload:
                continue

            source_entity = subject_payload[0]
            target_entity = object_payload[0]
            await self.repository.upsert_entity(source_entity)
            await self.repository.upsert_entity(target_entity)
            await self.repository.upsert_entity_relation(
                source_key=source_entity.key,
                target_key=target_entity.key,
                predicate=relation.get("predicate", "related_to"),
                evidence=relation.get("evidence", text[:500]),
                confidence=float(relation.get("confidence", 0.6)),
                chunk_id=chunk_id,
                source_quote=relation.get("evidence", ""),
            )
            linked += 1

        return linked

    def _stable_id(self, prefix: str, *parts: str) -> str:
        digest = hashlib.sha1("::".join(parts).encode("utf-8")).hexdigest()[:16]
        return f"{prefix}-{digest}"
