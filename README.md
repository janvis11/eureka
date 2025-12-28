# eureka.ai

Eureka is an intelligent research platform that helps scientists discover connections, identify research gaps, and generate hypotheses using AI-powered knowledge graphs and advanced RAG (Retrieval-Augmented Generation).

---

## Features

### Core Capabilities

- **Conversational Research (RAG)**: Natural language queries with AI-powered answers and citations using HuggingFace embeddings
- **Knowledge Graph**: Interactive visualization of research relationships and connections
- **Autonomous Discovery**: HuggingFace-powered AI agents identify research gaps, contradictions, and emerging trends
- **Hypothesis Generation**: HuggingFace models generate testable research hypotheses from identified gaps
- **Pattern Recognition**: Multi-agent analysis across domains and methodologies using HuggingFace models

### Discovery Pipeline

1. **Upload Papers** → PDF processing and text extraction
2. **RAG Chat** → Query papers using semantic search (HuggingFace embeddings)
3. **Discovery Analysis** → HuggingFace models analyze documents for:
   - Research gaps identification
   - Hypothesis generation
   - Trend detection
   - Contradiction detection

### Technical Highlights

- **Modern Stack**: React 18 + TypeScript + Vite + TailwindCSS
- **Production Ready**: Error boundaries, loading states, lazy loading, accessibility
- **Scalable Backend**: FastAPI with async/await, PostgreSQL, vector search
- **Developer Experience**: Hot module replacement, TypeScript strict mode, ESLint ready

---


## Quick Start

### 1. Clone Repository

```bash
git clone <repository-url>
cd eureka.ai
```

### 2. Frontend Setup

```bash
# Install dependencies
npm install

# Create environment file
cp .env.example .env

# Start development server
npm run dev
```

The frontend will be available at **http://localhost:3000**

### 3. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start backend server
python -m uvicorn app.main:app --reload --port 8000
```

The backend API will be available at **http://localhost:8000**

**API Documentation**: http://localhost:8000/docs

---


## Development

### Frontend Commands

```bash
# Development server with hot reload
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Type checking
npm run lint
```

### Backend Commands

```bash
# Development server with auto-reload
cd backend
uvicorn app.main:app --reload --port 8000

# Production server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Run tests (if available)
pytest tests/
```

### First-Time Setup

1. **Install Python dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **HuggingFace models download automatically** on first use:
   - Embedding model: `sentence-transformers/all-MiniLM-L6-v2` (~90MB)
   - Discovery model: `google/flan-t5-small` (~300MB)

3. **Optional: Configure models** in `backend/app/config.py`:
   ```python
   DISCOVERY_MODEL: str = "google/flan-t5-small"  # or flan-t5-base for better quality
   HF_USE_LOCAL_GENERATOR: bool = True
   ```

---

## Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# Backend API URL
VITE_API_BASE_URL=http://localhost:8000/api

# Optional: Debug mode
VITE_DEBUG=true
```

### Backend Configuration

Backend configuration is managed in `backend/app/config.py`. Key settings:

- Database connection
- API keys (HuggingFace, etc.)
- Model configurations
- CORS origins

---

## API Endpoints

### Document Management

- `POST /api/documents/upload` - Upload a research paper (PDF)
- `GET /api/documents` - List all uploaded documents
- `GET /api/documents/{id}` - Get document details

### Query Endpoints (RAG Chat)

- `POST /api/queries/ask` - Ask a question about uploaded documents
  ```json
  {
    "question": "What are the main findings?",
    "document_id": 1,  // Optional: query specific document
    "top_k": 5
  }
  ```
- `GET /api/queries/history` - Get query history

### Discovery Endpoints (HuggingFace-Powered)

- `POST /api/discovery/analyze` - Run full discovery analysis on all uploaded documents
  - Uses HuggingFace models to identify gaps, generate hypotheses, detect trends and contradictions
- `GET /api/discovery/gaps` - Get research gaps (from last analysis)
- `GET /api/discovery/hypotheses` - Get generated hypotheses
- `GET /api/discovery/trends` - Get trending topics
- `GET /api/discovery/contradictions` - Get detected contradictions

### Document Endpoints

- `POST /api/documents/upload` - Upload a research paper
- `GET /api/documents` - List all documents
- `GET /api/documents/{id}` - Get document details

**Full API Documentation**: http://localhost:8000/docs

---

