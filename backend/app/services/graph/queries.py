"""Cypher queries for Neo4j operations."""

# Schema initialization constraints
INIT_CONSTRAINTS = """
CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT entity_key IF NOT EXISTS FOR (e:Entity) REQUIRE e.key IS UNIQUE;
CREATE CONSTRAINT claim_id IF NOT EXISTS FOR (c:Claim) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT hypothesis_id IF NOT EXISTS FOR (h:Hypothesis) REQUIRE h.id IS UNIQUE;
CREATE CONSTRAINT research_gap_id IF NOT EXISTS FOR (g:ResearchGap) REQUIRE g.id IS UNIQUE;
"""

# Document upsert
UPSERT_DOCUMENT = """
MERGE (d:Document {id: $id})
SET d.title = $title,
    d.source_type = $source_type,
    d.created_at = $created_at,
    d.metadata_json = $metadata_json
RETURN d.id
"""

# Chunk upsert
UPSERT_CHUNK = """
MERGE (c:Chunk {id: $id})
SET c.text = $text,
    c.chunk_index = $chunk_index,
    c.token_count = $token_count,
    c.source_span_start = $source_span_start,
    c.source_span_end = $source_span_end
WITH c
MATCH (d:Document {id: $document_id})
MERGE (d)-[:CONTAINS]->(c)
RETURN c.id
"""

# Entity upsert
UPSERT_ENTITY = """
MERGE (e:Entity {key: $key})
SET e.name = $name,
    e.type = $type,
    e.aliases = $aliases,
    e.description = $description
RETURN e.key
"""

# Claim upsert
UPSERT_CLAIM = """
MERGE (c:Claim {id: $id})
SET c.text = $text,
    c.claim_type = $claim_type,
    c.polarity = $polarity,
    c.confidence = $confidence,
    c.source_quote = $source_quote
WITH c
OPTIONAL MATCH (chunk:Chunk {id: $chunk_id})
FOREACH (_ IN CASE WHEN chunk IS NOT NULL THEN [1] ELSE [] END |
    MERGE (chunk)-[:ASSERTS]->(c)
)
RETURN c.id
"""

# Link claim to entities
LINK_CLAIM_TO_ENTITIES = """
MATCH (c:Claim {id: $claim_id})
MATCH (e:Entity) WHERE e.key IN $entity_keys
FOREACH (entity IN CASE WHEN e IS NOT NULL THEN [1] ELSE [] END |
    MERGE (c)-[:ABOUT]->(e)
)
"""

# Link chunk to entities (MENTIONS relationship)
LINK_CHUNK_TO_ENTITIES = """
MATCH (c:Chunk {id: $chunk_id})
MATCH (e:Entity) WHERE e.key IN $entity_keys
FOREACH (x IN CASE WHEN e IS NOT NULL THEN [1] ELSE [] END |
    MERGE (c)-[:MENTIONS]->(e)
)
"""

# Link entities together with provenance. The relationship type stays generic
# so predicates can be data, while every edge still points back to a chunk.
UPSERT_ENTITY_RELATION = """
MATCH (a:Entity {key: $source_key})
MATCH (b:Entity {key: $target_key})
MERGE (a)-[r:RELATED {predicate: $predicate, chunk_id: $chunk_id}]->(b)
SET r.evidence = $evidence,
    r.confidence = $confidence,
    r.source_quote = $source_quote,
    r.updated_at = datetime(),
    r.seen_count = coalesce(r.seen_count, 0) + 1
RETURN elementId(r) AS relationship_id
"""

# Get entity neighborhood
GET_NEIGHBORHOOD = """
MATCH (e:Entity {key: $entity_key})
OPTIONAL MATCH path = (e)-[*1..3]-(neighbor)
WHERE length(path) <= $hops
  AND (neighbor:Entity OR neighbor:Claim OR neighbor:Document OR neighbor:Chunk)
WITH e, collect(DISTINCT neighbor) AS nodes, [p IN collect(DISTINCT path) WHERE p IS NOT NULL] AS paths
CALL {
    WITH paths
    UNWIND paths AS p
    UNWIND relationships(p) AS rel
    RETURN collect(DISTINCT {
        start: startNode(rel),
        type: type(rel),
        end: endNode(rel),
        predicate: rel.predicate,
        evidence: rel.evidence,
        confidence: rel.confidence,
        chunk_id: rel.chunk_id
    }) AS edges
}
RETURN e AS center, nodes, edges
"""

# Get a general graph overview for UI visualization
GET_GRAPH_OVERVIEW = """
MATCH (a)-[r]->(b)
WHERE size($relationship_types) = 0 OR type(r) IN $relationship_types
WITH a, r, b,
     CASE type(r)
        WHEN 'CONTAINS' THEN 0
        WHEN 'MENTIONS' THEN 1
        WHEN 'ASSERTS' THEN 2
        WHEN 'ABOUT' THEN 3
        WHEN 'RELATED' THEN 4
        ELSE 5
     END AS relation_priority
ORDER BY relation_priority ASC,
         toString(coalesce(a.title, a.name, a.key, a.id, elementId(a))) ASC
LIMIT $limit
WITH collect(DISTINCT {
        id: toString(coalesce(a.key, a.id, elementId(a))),
        label: toString(coalesce(a.name, a.title, a.key, a.id, left(coalesce(a.text, a.description, ''), 80), elementId(a))),
        kind: head(labels(a)),
        labels: labels(a),
        key: a.key,
        name: a.name,
        title: a.title,
        text: left(coalesce(a.text, a.source_quote, a.description, ''), 280),
        source_type: a.source_type,
        chunk_index: a.chunk_index,
        token_count: a.token_count,
        claim_type: a.claim_type,
        polarity: a.polarity,
        confidence: a.confidence
     }) +
     collect(DISTINCT {
        id: toString(coalesce(b.key, b.id, elementId(b))),
        label: toString(coalesce(b.name, b.title, b.key, b.id, left(coalesce(b.text, b.description, ''), 80), elementId(b))),
        kind: head(labels(b)),
        labels: labels(b),
        key: b.key,
        name: b.name,
        title: b.title,
        text: left(coalesce(b.text, b.source_quote, b.description, ''), 280),
        source_type: b.source_type,
        chunk_index: b.chunk_index,
        token_count: b.token_count,
        claim_type: b.claim_type,
        polarity: b.polarity,
        confidence: b.confidence
     }) AS raw_nodes,
     collect(DISTINCT {
        id: elementId(r),
        source: toString(coalesce(a.key, a.id, elementId(a))),
        target: toString(coalesce(b.key, b.id, elementId(b))),
        type: type(r),
        predicate: r.predicate,
        confidence: r.confidence,
        evidence: left(coalesce(r.evidence, r.source_quote, ''), 280),
        chunk_id: r.chunk_id
     }) AS edges
UNWIND raw_nodes AS node
WITH collect(DISTINCT node) AS nodes, edges
RETURN nodes, edges
"""

# Find bridge paths between two entities
FIND_BRIDGE_PATHS = """
MATCH path = (a:Entity {key: $source})-[*1..5]-(b:Entity {key: $target})
WHERE length(path) >= 2 AND length(path) <= $max_hops
RETURN path
LIMIT 25
"""

# Find underexplored gaps (entities that have evidence in different documents
# but few explicit graph relationships between them)
FIND_GAPS = """
MATCH (a)<-[:MENTIONS]-(:Chunk)<-[:CONTAINS]-(d1:Document)
MATCH (b)<-[:MENTIONS]-(:Chunk)<-[:CONTAINS]-(d2:Document)
WHERE a.key < b.key AND d1.id <> d2.id
OPTIONAL MATCH (a)-[r:RELATED]-(b)
WITH a, b, count(DISTINCT r) AS strength,
     count(DISTINCT d1) + count(DISTINCT d2) AS evidence_count
WHERE evidence_count >= 2 AND strength < 3
RETURN a.key AS a_key,
       b.key AS b_key,
       strength,
       evidence_count
ORDER BY evidence_count DESC, strength ASC
LIMIT 50
"""

# Find contradictory claims about an entity
FIND_CONTRADICTIONS = """
MATCH (e:Entity {key: $entity_key})<-[:ABOUT]-(c:Claim)
WITH c ORDER BY c.confidence DESC
LIMIT 10
MATCH (c1:Claim)-[:ABOUT]->(e)<-[:ABOUT]-(c2:Claim)
WHERE c1.id <> c2.id
  AND c1.polarity <> c2.polarity
  AND c1.polarity <> 'neutral'
  AND c2.polarity <> 'neutral'
RETURN c1.id AS claim_a_id,
       c1.text AS claim_a_text,
       c1.polarity AS claim_a_polarity,
       c2.id AS claim_b_id,
       c2.text AS claim_b_text,
       c2.polarity AS claim_b_polarity,
       (c1.confidence + c2.confidence) / 2.0 AS contradiction_score
ORDER BY contradiction_score DESC
LIMIT 20
"""

# Get claims by entity
GET_CLAIMS_BY_ENTITY = """
MATCH (e:Entity {key: $entity_key})<-[:ABOUT]-(c:Claim)
RETURN c ORDER BY c.confidence DESC
"""

# Get related documents for an entity
GET_RELATED_DOCUMENTS = """
MATCH (e:Entity {key: $entity_key})<-[:MENTIONS]-(c:Chunk)<-[:CONTAINS]-(d:Document)
RETURN DISTINCT d
ORDER BY d.created_at DESC
LIMIT 10
"""

# Community detection (uses GDS)
COMMUNITY_DETECTION = """
CALL gds.louvain.stream({
    nodeProjection: 'Entity',
    relationshipProjection: {
        RELATED: {
            type: '*',
            orientation: 'UNDIRECTED'
        }
    }
})
YIELD nodeId, communityId
RETURN gds.util.asNode(nodeId).key AS entity_key, communityId
ORDER BY communityId
"""

# Find trending concepts (recent + frequently mentioned)
FIND_TRENDING = """
MATCH (e:Entity)<-[:MENTIONS]-(c:Chunk)<-[:CONTAINS]-(d:Document)
WHERE d.created_at IS NULL OR datetime(d.created_at) >= datetime() - duration({days: $days})
RETURN e.key AS entity_key,
       e.name AS entity_name,
       e.type AS entity_type,
       count(DISTINCT d) AS document_count,
       count(DISTINCT c) AS mention_count
ORDER BY document_count DESC, mention_count DESC
LIMIT $limit
"""

# Upsert hypothesis
UPSERT_HYPOTHESIS = """
MERGE (h:Hypothesis {id: $id})
SET h.text = $text,
    h.novelty_score = $novelty_score,
    h.feasibility_score = $feasibility_score,
    h.falsifiability_score = $falsifiability_score,
    h.evidence_count = $evidence_count,
    h.experiment_plan = $experiment_plan,
    h.votes_up = coalesce(h.votes_up, 0),
    h.votes_down = coalesce(h.votes_down, 0)
RETURN h.id
"""

# Link hypothesis to supporting/counter claims
LINK_HYPOTHESIS_CLAIMS = """
MATCH (h:Hypothesis {id: $hypothesis_id})
OPTIONAL MATCH (c:Claim) WHERE c.id IN $supporting_ids
FOREACH (x IN CASE WHEN c IS NOT NULL THEN [1] ELSE [] END |
    MERGE (h)-[:SUPPORTED_BY]->(c)
)
OPTIONAL MATCH (c:Claim) WHERE c.id IN $counter_ids
FOREACH (x IN CASE WHEN c IS NOT NULL THEN [1] ELSE [] END |
    MERGE (h)-[:CONTRADICTED_BY]->(c)
)
"""

# Upsert research gap
UPSERT_GAP = """
MERGE (g:ResearchGap {id: $id})
SET g.description = $description,
    g.entity_keys = $entity_keys,
    g.evidence_count = $evidence_count,
    g.weakness_score = $weakness_score
RETURN g.id
"""
