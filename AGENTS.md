# AGENTS.md

## Commands

```bash
# backend
cd backend && pip install -r requirements.txt
cd backend && uvicorn app.main:app --reload
cd backend && pytest tests -q

# eval harness
python eval/run_eval.py
pytest eval/ -q

# frontend
npm install && npm run dev
npm run build          # tsc -b && vite build
npm run lint           # tsc --noEmit

# lint (backend)
cd backend && ruff check app     # config in backend/pyproject.toml, scoped to E9/F only
```

## Architecture

Read `docs/ARCHITECTURE.md` before touching retrieval or discovery code — it
has the request-path diagrams. Read `docs/DECISIONS.md` before making an
architectural change; check whether it already reverses a documented
decision, and add a new entry if it does. Read `docs/LIMITATIONS.md` before
claiming a feature is validated — most hypothesis-scoring dimensions are
heuristic, not measured.

## Gotchas

- Neo4j is optional at runtime. Every graph-dependent feature must degrade
  gracefully (catch the connection error, continue without graph context)
  — don't add a hard dependency on Neo4j being up.
- `EMBEDDING_DIM` in settings must match whatever the active embedding
  provider actually returns. `VectorRetriever` and `RAGEngine` both
  self-heal a dimension mismatch by rebuilding the FAISS index — don't
  remove that logic, and don't hardcode a dimension anywhere new.
- The model gateway (`app/services/model_gateway/`) auto-falls-back to a
  deterministic `fake` provider when no API key is set. Tests rely on this
  — don't require real API keys in unit tests.
- LLM JSON output is parsed with a regex `re.search(r"\{.*\}", ...)` plus
  `json.loads` in several places (`heuristic_priors.py`,
  `contradiction_verifier.py`, `hypothesis_validator.py`). This is fragile
  by design (fails closed, not silently) — if you touch one of these
  parsers, keep the fail-closed behavior.
- `app/services/discovery_engine.py` and `app/services/bridge_discovery.py`
  are legacy, kept only because `routers/discovery.py`'s `/analyze`
  endpoint still calls them. Don't add new features there — extend
  `app/services/discovery/` (the current package) instead.
- `backend/app/services/discovery/heuristic_priors.py` (renamed from
  `scoring.py`) intentionally labels which score dimensions are
  keyword-heuristic vs. retrieval-grounded (`basis` field). Don't remove
  that labeling when editing scoring logic.
- `eval/gold/*.jsonl` currently contains illustrative example rows, not
  real hand-labeled ground truth — don't treat numbers from
  `eval/run_eval.py` as submission-ready without checking
  `is_example_data` in the output.

## Code style

Python: type-hinted, `async`/`await` throughout the service layer, no
comments explaining *what* code does — only *why*, when non-obvious.
Mirror existing per-task LLM temperatures (extraction/navigation 0.1,
rerank 0.0, grounded generation 0.2, hypothesis generation 0.4) rather than
introducing a new default.

## Never reference the buildathon

This project is a real product, not a competition submission. Never add
"Razorpay," "buildathon," "win plan," or judging-axis language to any
committed file — README, docs, code comments, or commit messages.
