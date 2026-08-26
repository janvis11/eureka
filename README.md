# Eureka - an AI-native research discovery platform

Eureka turns a pile of research papers into a living knowledge graph.
Upload papers and it extracts concepts, claims, methods, and evidence,
then lets you ask questions, trace evidence, detect research gaps, surface
contradictions, spot trends, and generate testable hypotheses — not just
search or summarize one paper at a time.

Generated discoveries are candidates, not facts. Eureka assists scientific
reasoning; it doesn't replace scientific validation.

[Live demo](https://eureka-ai.onrender.com/) ·
[Architecture](docs/ARCHITECTURE.md) ·

[![CI](https://github.com/janvis11/eureka/actions/workflows/ci.yml/badge.svg)](https://github.com/janvis11/eureka/actions/workflows/ci.yml)

## Core capabilities

- **Knowledge graph** — papers, concepts, claims, and relationships (Neo4j)
- **Hybrid RAG** — BM25 + vector + graph retrieval with source-grounded, cited answers
- **Gap detection** — finds under-explored spaces in the literature
- **Contradiction detection** — surfaces conflicting claims across papers
- **Hypothesis generation & validation** — proposes and scores testable hypotheses
- **Trend analysis** — concepts and methods gaining traction across the corpus
- **Abstention** — says "not enough evidence" instead of guessing when retrieval is weak

## How it works

1. Upload papers → extract text, sections, and chunks.
2. Extract concepts, claims, methods, and evidence into a knowledge graph.
3. Ask questions from one paper or the full corpus.
4. Run discovery workflows for gaps, contradictions, trends, and hypotheses.

## Tech stack

**Frontend:** React, TypeScript, Vite, Tailwind CSS

**Backend:** FastAPI, Python, SQLAlchemy (SQLite locally, Postgres in
prod), FAISS for vector search, Neo4j for the knowledge graph, Groq for
generation with OpenAI-compatible embeddings and a local fallback

## Run it

```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env   # fill in GROQ_API_KEY or OPENAI_API_KEY
uvicorn app.main:app --reload

# Frontend (separate terminal, from repo root)
npm install
npm run dev
```

Or via Docker: `docker compose up`.
