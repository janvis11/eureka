# eureka.ai

eureka.ai is an ai-native research discovery platform built for scientific literature.

it is designed to help researchers move beyond normal document search into advanced rag, knowledge graph reasoning, gap detection, contradiction detection, hypothesis generation, hypothesis validation, trend intelligence, evidence tracing, and discovery workflows.

the product turns a pile of research papers into a living knowledge graph where papers, concepts, claims, methods, evidence, contradictions, research gaps, and emerging hypotheses can be explored together.

eureka.ai is being built as a real research infrastructure product for scientists, labs, students, founders, and deep-tech teams.

## problem

scientific knowledge is growing faster than humans can read.

researchers often need to understand hundreds of papers before they can form a useful research question. important ideas are buried across abstracts, methods, results, limitations, citations, and small claims inside papers.

current tools are limited:

- search engines find documents, not discoveries
- chatbots summarize papers, but do not build scientific structure
- basic rag answers questions, but often misses gaps, contradictions, and weak evidence
- literature reviews are slow, manual, and hard to update
- hidden connections across papers are usually discovered by accident

the real bottleneck is not access to papers. the bottleneck is reasoning across them.

## solution

eureka.ai converts uploaded research papers into a structured discovery workspace.

it extracts paper text, sections, concepts, claims, methods, evidence, and relationships. then it builds a knowledge graph and combines it with advanced rag so users can ask questions, trace evidence, inspect relationships, detect research gaps, discover contradictions, identify trends, and generate testable hypotheses.

the system is built for research workflows where the answer is not always written directly in one paragraph. many valuable insights come from comparing papers, connecting distant concepts, and finding what the literature does not explain yet.

## core capabilities

- pdf upload and batch paper ingestion
- structured paper parsing
- section-aware rag
- vector-based retrieval
- paper-scoped chat
- source-grounded answers
- citation and evidence tracing
- knowledge graph construction
- concept extraction
- claim extraction
- graph-based discovery
- research gap detection
- contradiction detection
- hypothesis generation
- hypothesis validation support
- counter-evidence tracking
- trend analysis across papers
- neo4j graph storage
- local development database
- local embedding fallback when api embeddings fail

## discovery engine

eureka.ai is not only a question-answering layer.

it is built around discovery primitives:

- `knowledge graph`: maps papers, concepts, chunks, claims, hypotheses, and relationships
- `gap detection`: finds under-explored spaces and missing links in the literature
- `contradiction detection`: surfaces conflicting claims and incompatible evidence
- `hypothesis generation`: proposes testable candidate hypotheses from graph patterns
- `hypothesis validation`: connects hypotheses to supporting evidence, counter-evidence, novelty, feasibility, and falsifiability
- `trend analysis`: identifies concepts and methods gaining importance across papers
- `advanced rag`: retrieves evidence from paper structure, vector similarity, and graph context

generated discoveries are candidates, not facts. the platform assists scientific reasoning; it does not replace scientific validation.

## how it works

1. upload research papers.
2. extract text, metadata, sections, and chunks.
3. index the paper for structured rag and vector retrieval.
4. extract concepts, claims, methods, and evidence.
5. write documents, chunks, entities, claims, and relationships into neo4j.
6. ask questions from one paper or the full corpus.
7. inspect graph connections and evidence paths.
8. run discovery workflows for gaps, contradictions, trends, and hypotheses.
9. validate candidate hypotheses with evidence, counter-evidence, and testability signals.

## product pages

- `home`: product introduction and discovery theme
- `workspace`: upload, manage, and delete papers
- `chat`: ask questions with paper context
- `graph`: inspect knowledge graph statistics and paths
- `discover`: run gap, trend, and contradiction workflows
- `hypothesis`: generate and review candidate hypotheses

## tech stack

frontend:

- react
- typescript
- vite
- tailwind css

backend:

- fastapi
- python
- sqlalchemy
- sqlite for local development
- Render Postgres for hosted deployment
- faiss for vector search
- neo4j for graph storage
- groq for llm generation
- openai-compatible embeddings when available
- local lexical embeddings as fallback

