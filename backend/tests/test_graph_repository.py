import pytest

from app.services.graph.repository import GraphRepository


class FakeGraphClient:
    def __init__(self):
        self.query = ""
        self.params = {}

    async def execute_write(self, query, params):
        self.query = query
        self.params = params
        if "MATCH (d:Document" in query:
            return {
                "documents_deleted": 1,
                "chunks_deleted": 4,
                "claims_deleted": 2,
                "orphan_entities_deleted": 3,
            }
        return {"id": params["id"], "votes_up": 3, "votes_down": 1}


@pytest.mark.asyncio
async def test_vote_hypothesis_updates_graph_vote_count():
    client = FakeGraphClient()
    repo = GraphRepository(client=client)

    result = await repo.vote_hypothesis("hyp-graph-123", "up")

    assert result == {"votes_up": 3, "votes_down": 1}
    assert client.params == {"id": "hyp-graph-123"}
    assert "h.votes_up = coalesce(h.votes_up, 0) + 1" in client.query
    assert "h.votes_down = coalesce(h.votes_down, 0)" in client.query


@pytest.mark.asyncio
async def test_delete_document_removes_owned_graph_nodes():
    client = FakeGraphClient()
    repo = GraphRepository(client=client)

    result = await repo.delete_document("42")

    assert result == {
        "documents_deleted": 1,
        "chunks_deleted": 4,
        "claims_deleted": 2,
        "orphan_entities_deleted": 3,
    }
    assert client.params == {"id": "42"}
    assert "MATCH (d:Document {id: $id})" in client.query
    assert "DETACH DELETE d" in client.query
    assert "orphan_entities_deleted" in client.query
