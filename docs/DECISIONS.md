# Decisions

Short ADRs. Format: Decision / Why / What I rejected / What it cost me.

## 1. Provider-agnostic model gateway instead of a single SDK

**Decision:** All LLM/embedding calls go through a `ModelGateway` protocol
(`generate`, `embed`, `rerank`) with swappable providers (`groq`, `openai`
and OpenAI-compatible endpoints, a deterministic `fake` provider, and a
local lexical embedding fallback).

**Why:** The system needs to run in tests and local dev with zero network
calls (`fake` provider), needs to survive an embedding API being
unavailable without crashing (local fallback), and shouldn't be locked
into one vendor's rate limits or pricing on a tight hosting budget.

**What I rejected:** Calling the Groq/OpenAI SDKs directly from business
logic, or adopting LangChain's abstraction layer for this. Direct SDK calls
would have meant no `fake` provider and no clean fallback path. LangChain's
abstractions are heavier than this project needs — the actual surface area
here is three methods, and LangChain's chain/agent abstractions would have
added indirection without solving a problem this project actually has.

**What it cost me:** Every provider has to reimplement the same
plumbing (JSON-mode parsing, error handling, rerank passthrough for
providers that don't support it natively). `openai_provider.py` and
`groq_provider.py`'s embed methods duplicate the `dimensions` parameter
fix almost verbatim — a small amount of duplication traded for not having
a shared base class hide provider-specific quirks.

## 2. FAISS, not a hosted vector DB

**Decision:** Vector search uses `faiss.IndexFlatIP`/`IndexFlatL2` in
process, persisted to disk, not a hosted service like Pinecone or a
managed Chroma/Weaviate instance.

**Why:** The deploy has no budget for a hosted vector DB
subscription, and the corpus size (tens of papers, thousands of chunks)
is well within what an in-process flat index handles without needing
approximate search. FAISS also has zero network dependency, which matters
for the "does this survive Render free-tier cold starts" question.

**What I rejected:** A hosted vector DB (better at scale, handles
persistence and replication for you) and FAISS's own approximate indexes
(`IndexIVFFlat`, HNSW — faster at scale, but exact search is simpler to
reason about and fast enough at this corpus size).

**What it cost me:** Persistence is hand-rolled (`_save_index`/`_load_index`
in `rag_engine.py`, pickle for metadata) instead of being someone else's
problem, and it doesn't survive Render's ephemeral `/tmp` on the free tier
(see `docs/LIMITATIONS.md`). This is the actual cost, and it's real —
a hosted store with persistent storage would not have this failure mode.

## 3. Two-stage contradiction detection: keyword miner + LLM verifier

**Decision:** `ContradictionMiner` (antonym/keyword pass) generates
candidates; `ContradictionVerifier` (LLM call, 3-way verdict) filters them.
Neither stage runs alone.

**Why:** A pure-keyword approach has poor precision — same-entity,
opposite-polarity claims are very often just claims from different
populations, dosages, or timeframes, not real contradictions. A pure-LLM
approach (ask the LLM to find contradictions directly) would be
expensive to run over every claim pair in a corpus and would need to
implicitly do the "same entity" grouping the miner does for free.

**What I rejected:** LLM-only contradiction detection over the full claim
set (O(n²) LLM calls before any cheap filtering) and keyword-only detection
(cheap but the false-positive rate makes the feature untrustworthy).

**What it cost me:** One LLM call per *candidate* pair (not per claim
pair) — still O(candidates), so a corpus with many same-entity claims
still means many verifier calls. The miner's keyword list also determines
recall at the top of the funnel: a contradiction that doesn't use one of
the antonym pairs (`improves`/`reduces`, etc.) never reaches the verifier
at all. See `docs/LIMITATIONS.md`.

## 4. Neo4j for the knowledge graph instead of keeping everything relational

**Decision:** Papers, concepts, claims, and their relationships are
written into Neo4j (`app/services/graph/`) alongside the relational
Postgres/SQLite store for documents and query history.

**Why:** Gap detection, bridge discovery, and trend analysis are
fundamentally graph-traversal problems (shortest paths between concepts,
neighborhood queries, path length as a novelty signal). Expressing those
as SQL joins over a documents/claims table would mean either N+1 queries
or increasingly unreadable recursive CTEs for anything more than one hop.

**What I rejected:** Modeling the same relationships as foreign-key tables
in Postgres, or an in-memory graph library (`networkx`, which is used
elsewhere in the stack for lighter analysis) as the only graph
representation.

**What it cost me:** A second database to run, configure, and handle
failures for. Every graph-dependent feature needs a "Neo4j unreachable"
fallback path — the graph retriever, bridge finder, and trend radar all
have to degrade gracefully instead of assuming Neo4j is always up.

## 5. Confidence-gated abstention before generation, not after

**Decision:** `RAGEngine.generate_answer` computes retrieval confidence
(`confidence.py`) and returns a structured abstention *before* calling the
LLM when confidence is below threshold, rather than asking the LLM to
answer and hoping it says "I don't know" when it should.

**Why:** LLMs are unreliable narrators of their own uncertainty — a model
asked to answer from weak context will often produce a fluent, confident-
sounding answer anyway, especially at low temperature. Gating on retrieval
signal (similarity, source diversity) before generation means the system
never has to trust the model's self-report, and it also saves a
generation call on the failure path.

**What I rejected:** Prompting the LLM to say "insufficient evidence" when
unsure (already tried in the prompt text — kept as a second line of
defense, but not the primary abstention mechanism) and a hard evidence-
count threshold alone (rejected because a single very strong match should
be able to answer, and three weak, redundant matches from one document
should not).

**What it cost me:** The confidence formula is a hand-tuned linear blend
of heuristic signals, not a calibrated probability, and it hasn't been
validated against labeled answerable/unanswerable questions yet — see
`docs/LIMITATIONS.md`. It's also only wired into one of the three answer
paths in the codebase.

## 6. Renaming `scoring.py` to `heuristic_priors.py` instead of leaving it as-is

**Decision:** The hypothesis scoring module was renamed, and every score it
returns now carries a `basis` tag (`heuristic_keyword_match` vs.
`retrieval_grounded`) plus an explicit disclaimer string.

**Why:** Four of five scoring dimensions (`novelty`, `impact`,
`feasibility`, `falsifiability`) are keyword-matching heuristics against
LLM-generated text, not validated measurements — an LLM that writes
"dramatically" scores higher on impact regardless of whether the
hypothesis is any good. Calling that module `scoring.py` and returning a
number called `overall` invites treating it as a measurement instead of a
sort key.

**What I rejected:** Leaving the module and its output shape unchanged
(the "say nothing" option) and rewriting the heuristics into something
that claims to be validated without actually being backed by evaluated
ground truth (the "pretend it's fixed" option — worse than doing nothing).

**What it cost me:** Nothing functionally changed — the ranking behavior
is identical. The cost is entirely upside: any caller or reviewer reading
the output now sees the honesty label instead of discovering the keyword
matching by opening the file.

## 7. Keeping the legacy discovery engine reachable instead of deleting it

**Decision:** `app/services/discovery_engine.py` and
`app/services/bridge_discovery.py` are marked legacy in their module
docstrings but not deleted, because `routers/discovery.py`'s `/analyze`
endpoint still depends on them for full-text (non-graph) analysis.

**Why:** Deleting them outright would break that endpoint's current
behavior with no replacement ready. The honest options were: delete and
accept a regression, silently keep both with no signal about which is
current, or label clearly and keep both working until the endpoint is
ported. I chose the third.

**What I rejected:** Deleting on the assumption the endpoint is unused
(risk of breaking a live code path without verifying every caller) and
silently leaving both modules unlabeled (the state this decision replaces
— indistinguishable current vs. legacy code is a real build-quality
penalty).

**What it cost me:** Two separate contradiction-detection implementations
still coexist in the codebase (`contradiction_graph.py` in the legacy
path, `contradiction_miner.py`/`contradiction_verifier.py` in the current
one) until `/analyze` is ported onto the current engine. See
`docs/LIMITATIONS.md`.
