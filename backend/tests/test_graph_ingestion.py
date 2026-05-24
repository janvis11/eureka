import pytest

from app.services.graph.ingestion import GraphIngestionPipeline, normalize_entity_key
from app.services.model_gateway.fake_provider import FakeProvider


class FakeGraphRepository:
    def __init__(self):
        self.documents = []
        self.chunks = []
        self.entities = {}
        self.claims = []
        self.chunk_entity_links = []
        self.claim_entity_links = []
        self.relationships = []

    async def upsert_document(self, doc):
        self.documents.append(doc)
        return doc.id

    async def upsert_chunk(self, chunk):
        self.chunks.append(chunk)
        return chunk.id

    async def upsert_entity(self, entity):
        self.entities[entity.key] = entity
        return entity.key

    async def link_chunk_to_entities(self, chunk_id, entity_keys):
        self.chunk_entity_links.append((chunk_id, list(entity_keys)))
        return len(entity_keys)

    async def upsert_claim(self, claim):
        self.claims.append(claim)
        return claim.id

    async def link_claim_to_entities(self, claim_id, entity_keys):
        self.claim_entity_links.append((claim_id, list(entity_keys)))
        return len(entity_keys)

    async def upsert_entity_relation(
        self,
        source_key,
        target_key,
        predicate,
        evidence,
        confidence,
        chunk_id,
        source_quote="",
    ):
        self.relationships.append(
            {
                "source_key": source_key,
                "target_key": target_key,
                "predicate": predicate,
                "evidence": evidence,
                "confidence": confidence,
                "chunk_id": chunk_id,
                "source_quote": source_quote,
            }
        )
        return str(len(self.relationships))


@pytest.mark.asyncio
async def test_graph_ingestion_persists_provenance_rich_nodes_and_edges():
    repo = FakeGraphRepository()
    pipeline = GraphIngestionPipeline(repository=repo, gateway=FakeProvider())

    counts = await pipeline.ingest_document(
        document_id="1",
        title="Graph RAG for Drug Discovery",
        metadata={"title": "Graph RAG for Drug Discovery"},
        chunks=[
            {
                "chunk_index": 0,
                "text": (
                    "Graph RAG improves biomedical retrieval accuracy. "
                    "The proposed Graph RAG framework shows better evidence tracing "
                    "for Drug Discovery but is limited by sparse validation data."
                ),
            }
        ],
        full_text="Graph RAG improves biomedical retrieval accuracy.",
    )

    assert counts["documents"] == 1
    assert counts["chunks"] == 1
    assert counts["entities"] > 0
    assert counts["claims"] > 0
    assert counts["relationships"] > 0
    assert repo.documents[0].metadata["title"] == "Graph RAG for Drug Discovery"
    assert repo.chunks[0].document_id == "1"
    assert repo.claims[0].source_quote
    assert all(rel["chunk_id"] == "doc_1_chunk_0" for rel in repo.relationships)


def test_normalize_entity_key_uses_roadmap_shape():
    assert normalize_entity_key("Graph RAG", "METHOD") == "graph-rag:METHOD"
