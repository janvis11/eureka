# 🔬 Eureka Discovery Pipeline

## Overview

Eureka uses a **two-stage pipeline** for research discovery:

1. **Document Upload & RAG Chat** - Upload papers and query them
2. **Discovery Analysis** - AI-powered discovery using HuggingFace models

---

## Pipeline Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    STAGE 1: DOCUMENT PROCESSING              │
└─────────────────────────────────────────────────────────────┘

1. Upload PDF → Document Processor
   ↓
2. Extract Text → Chunk into segments
   ↓
3. Generate Embeddings (HuggingFace: sentence-transformers)
   ↓
4. Store in Vector DB (FAISS) → Ready for RAG queries

┌─────────────────────────────────────────────────────────────┐
│                    STAGE 2: RAG CHAT                        │
└─────────────────────────────────────────────────────────────┘

1. User asks question → Semantic Search (HuggingFace embeddings)
   ↓
2. Retrieve relevant chunks → Context building
   ↓
3. Generate answer (Groq LLM) → Response with citations

┌─────────────────────────────────────────────────────────────┐
│                    STAGE 3: DISCOVERY                       │
└─────────────────────────────────────────────────────────────┘

1. Run Discovery Analysis → Uses ALL uploaded documents
   ↓
2. HuggingFace Models analyze documents for:
   ├─ Research Gaps (HF text2text-generation)
   ├─ Hypothesis Generation (HF text2text-generation)
   ├─ Trend Detection (HF text2text-generation)
   └─ Contradiction Detection (HF text2text-generation)
   ↓
3. Results stored → Available via API endpoints
```

---

## API Endpoints

### 1. Upload Documents

```bash
POST /api/documents/upload
Content-Type: multipart/form-data

# Upload PDF file
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@research_paper.pdf"
```

**Response:**
```json
{
  "id": 1,
  "filename": "research_paper.pdf",
  "status": "processing",
  "message": "Document uploaded successfully and processing in background"
}
```

### 2. Query Documents (RAG Chat)

```bash
POST /api/queries/ask
Content-Type: application/json

{
  "question": "What are the main findings in the uploaded papers?",
  "document_id": 1,  // Optional: query specific document
  "top_k": 5
}
```

**Response:**
```json
{
  "query_id": 1,
  "answer": "Based on the uploaded documents...",
  "sources": [
    {
      "document_id": "1",
      "title": "Research Paper Title",
      "relevance_score": 0.95,
      "text_preview": "..."
    }
  ],
  "confidence": 0.87,
  "retrieved_chunks": 5
}
```

### 3. Run Discovery Analysis

```bash
POST /api/discovery/analyze
```

**Response:**
```json
{
  "discovery_id": 1,
  "analysis": {
    "gaps": [
      {
        "id": "gap-1",
        "title": "Missing validation methodology",
        "description": "...",
        "type": "methodological",
        "impact": "high",
        "confidence": 0.85
      }
    ],
    "hypotheses": [
      {
        "text": "Implementing X methodology will improve Y",
        "rationale": "...",
        "methodology": "...",
        "confidence": 0.75
      }
    ],
    "contradictions": [...],
    "trends": [...],
    "summary": {
      "gaps_found": 5,
      "hypotheses_generated": 8,
      "contradictions_detected": 2,
      "trends_identified": 12
    }
  }
}
```

### 4. Get Discovery Results

```bash
# Get gaps
GET /api/discovery/gaps

# Get hypotheses
GET /api/discovery/hypotheses

# Get trends
GET /api/discovery/trends

# Get contradictions
GET /api/discovery/contradictions
```

---

## HuggingFace Models Used

### 1. Embeddings (RAG)
- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Purpose**: Generate embeddings for semantic search
- **Usage**: Document chunks and queries

### 2. Discovery Generation
- **Model**: `google/flan-t5-small` (configurable)
- **Purpose**: Generate discovery insights
- **Tasks**:
  - Research gap identification
  - Hypothesis generation
  - Trend analysis
  - Contradiction detection

### Configuration

Edit `backend/app/config.py`:

```python
# Discovery model (for gap/hypothesis/trend generation)
DISCOVERY_MODEL: str = "google/flan-t5-small"

# Use local HF generator
HF_USE_LOCAL_GENERATOR: bool = True
```

**Alternative Models** (if you have GPU):
- `google/flan-t5-base` - Better quality, slower
- `google/flan-t5-large` - Best quality, requires GPU
- `microsoft/DialoGPT-medium` - For conversational discovery

---

## Usage Example

### Complete Workflow

```python
# 1. Upload multiple papers
papers = ["paper1.pdf", "paper2.pdf", "paper3.pdf"]
for paper in papers:
    upload_document(paper)

# 2. Wait for processing (check status)
# Documents are processed in background

# 3. Query papers using RAG
response = ask_question(
    question="What are the main research gaps?",
    document_id=None  # Query all documents
)

# 4. Run discovery analysis
discovery = run_discovery_analysis()
# This uses HuggingFace models to analyze ALL uploaded documents

# 5. Get discovery results
gaps = get_research_gaps()
hypotheses = get_hypotheses()
trends = get_trends()
```

---

## How Discovery Works

### Research Gap Detection

1. **Input**: All uploaded document texts
2. **Process**: 
   - HF model analyzes document content
   - Identifies missing/under-explored areas
   - Categorizes gaps (methodological, theoretical, empirical)
3. **Output**: List of research gaps with confidence scores

### Hypothesis Generation

1. **Input**: Research gaps + document context
2. **Process**:
   - HF model generates testable hypotheses for each gap
   - Includes rationale, methodology, expected impact
3. **Output**: Testable research hypotheses

### Trend Detection

1. **Input**: All document texts
2. **Process**:
   - HF model identifies frequently discussed topics
   - Analyzes growth patterns and emerging concepts
3. **Output**: Trending topics with growth metrics

### Contradiction Detection

1. **Input**: Document pairs
2. **Process**:
   - HF model compares documents for conflicting findings
   - Identifies opposing methodologies or conclusions
3. **Output**: List of contradictions with confidence scores

---

## Performance Tips

1. **Batch Processing**: Discovery runs on all documents at once
2. **Model Selection**: Use smaller models (flan-t5-small) for CPU, larger for GPU
3. **Document Limits**: Discovery analyzes up to 5 documents at a time for prompt size limits
4. **Caching**: Embeddings are cached to avoid recomputation

---

## Troubleshooting

### Discovery returns empty results

- **Check**: Are documents processed? (`GET /api/documents`)
- **Check**: Do documents have content? (processing_status = "completed")
- **Solution**: Wait for document processing to complete

### HF model errors

- **Check**: Is `HF_USE_LOCAL_GENERATOR=True`?
- **Check**: Are transformers installed? (`pip install transformers`)
- **Solution**: Models download automatically on first use

### Slow discovery

- **Cause**: Large documents or many documents
- **Solution**: 
  - Use smaller models for faster inference
  - Limit document count in analysis
  - Use GPU if available

---

## Next Steps

1. Upload research papers
2. Query them using RAG chat
3. Run discovery analysis
4. Explore gaps, hypotheses, trends, and contradictions!

**Happy Discovering! 🔬✨**

