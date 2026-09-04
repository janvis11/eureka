# Limitations

What doesn't work, what's heuristic rather than validated, and what's
untested. This list exists because a discovered heuristic behind a score
that claims to be objective is worse for trust than stating it up front.

## Heuristic, not validated

- **Hypothesis scoring** (`backend/app/services/discovery/heuristic_priors.py`,
  renamed from `scoring.py`): only `evidence_strength` is grounded in real
  signal (retrieval scores, counter-evidence counts). `novelty`, `impact`,
  `feasibility`, and `falsifiability` are keyword/substring matches against
  LLM-generated hypothesis text — a hypothesis that happens to say
  "dramatically" scores higher on impact regardless of merit. Every score
  the module returns now carries a `basis` tag (`heuristic_keyword_match`
  vs `retrieval_grounded`) so callers can't present it as validated by
  accident, but the underlying signal itself hasn't changed.
- **Retrieval confidence / abstention** (`backend/app/services/retrieval/confidence.py`):
  blends top-1 similarity, average similarity, and source diversity from a
  FAISS L2 distance normalized by `1 - distance/100` — a reasonable
  heuristic, not a calibrated probability. It has not been validated
  against labeled answerable/unanswerable questions (that requires a real
  gold `qa.jsonl` set, not the illustrative examples currently there). A
  fuller confidence model would also want rerank agreement and graph
  corroboration as signals; neither is wired in yet.
- **Contradiction candidate generation** (`contradiction_miner.py`): still a
  same-entity, opposite-polarity keyword pass (`improves`/`reduces`,
  `increases`/`decreases`, exact metric-value conflicts). It's meant only as
  a high-recall candidate generator now that a verification stage exists —
  see below — but it can still miss contradictions that don't share
  antonym-pair keywords.

## Implemented but not yet evaluated against real labels

- **Two-stage contradiction verification**
  (`contradiction_verifier.py` + `contradiction_miner.py`): the LLM
  verifier classifies each candidate pair as `CONTRADICTION` /
  `CONTEXT_DIFFERENCE` / `NOT_RELATED` and is unit-tested against scripted
  LLM responses (`backend/tests/test_contradiction_verifier.py`) and
  end-to-end against 5 illustrative example pairs
  (`eval/gold/contradictions.jsonl`, run via `python eval/run_eval.py`).
  Those 5 pairs are not a real gold set — a trustworthy eval needs on the
  order of 60–80 hand-labeled pairs. Until that exists, there is no real
  precision/recall number for this feature, only a demonstration that the
  pipeline runs.
- **Abstention gate**: wired into `RAGEngine.generate_answer`, the code
  path behind `/api/queries/ask`'s vector-search fallback, and covered by
  unit tests. It is **not** wired into the structural RAG path
  (`structural_rag_engine.py`, used when documents have structural indexes)
  or into the discovery engine's answer composition
  (`answer_composer.py`, which computes its own separate confidence score
  and is not currently called by any router). Confidence values from these
  three paths are not comparable to each other.
- **Retrieval, grounding, claim-extraction metrics**: implemented and unit
  tested (`eval/metrics.py`, `eval/test_metrics.py`) but not runnable
  end-to-end yet — they need a demo corpus (not built) and real
  hand-labeled questions/paragraphs (not built). `eval/run_eval.py`
  reports these as `NOT RUN` with the specific missing input rather than
  a fabricated number.

## Newly added, not yet measured

- **Reranking is on by default** (`settings.USE_RERANKER = True`,
  `HybridRetriever`) but there is no retrieval ablation yet proving it's
  worth its added latency/cost on this corpus — see
  `docs/DECISIONS.md` #9. Turning it off and comparing is one command
  (`USE_RERANKER=false`) away; the eval to actually do that comparison
  doesn't exist yet.
- **Citation grounding is not enforced at generation time.** `eval/metrics.py`
  has `verbatim_grounding_rate` to *measure* whether cited quotes appear
  verbatim in their source chunk, but nothing in the live answer path
  extracts per-citation quotes to check — `rag_engine.py`'s prompt doesn't
  ask for structured citations, only a source-numbered context block.
  Wiring this properly needs the generation prompt to output
  claim-to-quote citations, not just a bracketed source index; that's a
  prompt/output-format change, not a plug-in check, and hasn't been done.
- **Retry/backoff on provider calls** (`app/services/model_gateway/retry.py`)
  is untested against a real rate-limited or flaky provider — only that it
  doesn't break the existing fallback paths (unit tests pass). Worst-case
  added latency per call is ~11s (three attempts, exponential backoff up
  to 8s) before falling through to existing error handling.
- **NVIDIA NIM (Nemotron) is now the default provider, untested live.**
  `NvidiaProvider` is verified against a mocked client only
  (`tests/test_nvidia_provider.py`) — it has not made a real call against
  `https://integrate.api.nvidia.com/v1`. Specific unknowns: whether
  disabling "thinking" mode actually produces clean JSON output on every
  Nemotron 3 model size, whether free-tier rate limits are survivable for
  real traffic (NVIDIA publishes no SLA; third-party reports describe fast
  429s independent of request rate), and whether `guided_json` should
  replace plain `json_mode` for stricter output validation. See
  `docs/DECISIONS.md` #10.

## Not fixed

- **Ephemeral demo storage**: `render.yaml` still points
  `UPLOAD_DIR`/`CHROMADB_PATH` at `/tmp/eureka/...` on Render's free tier.
  Uploaded PDFs and the FAISS index are lost on every restart/spin-down. No
  pre-seeded demo corpus exists yet, so a fresh deploy currently has no
  documents until someone uploads them again.
- **No dedicated auth system**: the API relies on CORS + `TrustedHostMiddleware`
  only; there's no user auth/session layer.

## Legacy code kept for compatibility, not because it's the right design

- `backend/app/services/discovery_engine.py` and
  `backend/app/services/bridge_discovery.py` are the pre-Neo4j discovery
  pipeline. They're marked as legacy in their module docstrings and are
  not part of the current design (`app/services/discovery/engine.py` +
  `app/services/graph/`), but `routers/discovery.py`'s `/analyze` endpoint
  still calls the legacy engine for full-text analysis, so they can't be
  deleted without either replacing that endpoint's behavior or accepting a
  regression in what it can analyze. Contradiction detection in that legacy
  path (`contradiction_graph.py`) is a separate implementation from
  `contradiction_miner.py`/`contradiction_verifier.py` and was not touched
  by the two-stage verifier work above.

## What would change with 3 more months

- A held-out labeled eval big enough to trust (on the order of 40 QA
  pairs, 70 contradiction pairs, 30 claim-extraction paragraphs), with the
  retrieval/grounding/abstention harness actually running against it.
- Retire the legacy discovery engine by porting `/analyze`'s full-text mode
  onto the current graph-backed pipeline, so there's one contradiction
  implementation instead of two.
- A confidence model with a real calibration curve (reliability diagram)
  instead of a hand-tuned linear blend of similarity signals.
- Unify the three separate confidence/abstention implementations
  (`rag_engine.py`, `structural_rag_engine.py`, `answer_composer.py`) into
  one.
