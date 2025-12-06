# 🔬 Eureka AI - Scientific Discovery Platform

> **AI-Powered Research Assistant** | React + TypeScript Frontend | FastAPI Backend

Eureka is an intelligent research platform that helps scientists discover connections, identify research gaps, and generate hypotheses using AI-powered knowledge graphs and advanced RAG (Retrieval-Augmented Generation).

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![TypeScript](https://img.shields.io/badge/TypeScript-5.3-blue.svg)
![React](https://img.shields.io/badge/React-18.3-blue.svg)

---

## 🎯 Features

### Core Capabilities

- **🤖 Conversational Research (RAG)**: Natural language queries with AI-powered answers and citations using HuggingFace embeddings
- **🕸️ Knowledge Graph**: Interactive visualization of research relationships and connections
- **🔍 Autonomous Discovery**: HuggingFace-powered AI agents identify research gaps, contradictions, and emerging trends
- **💡 Hypothesis Generation**: HuggingFace models generate testable research hypotheses from identified gaps
- **📊 Pattern Recognition**: Multi-agent analysis across domains and methodologies using HuggingFace models

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

## 📋 Prerequisites

### Frontend
- **Node.js** 18+ ([Download](https://nodejs.org/))
- **npm** 7+ (comes with Node.js)

### Backend
- **Python** 3.10+ ([Download](https://www.python.org/downloads/))
- **PostgreSQL** 14+ (optional, for production)
- **ChromaDB** (embedded, no setup needed)

---

## 🚀 Quick Start

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

## 📁 Project Structure

```
eureka.ai/
├── src/                      # Frontend React application
│   ├── components/          # Reusable UI components
│   │   ├── Navbar.tsx       # Navigation bar
│   │   ├── Footer.tsx       # Footer component
│   │   └── ErrorBoundary.tsx # Error handling
│   ├── pages/               # Page components
│   │   ├── LandingPage.tsx  # Home page
│   │   ├── ChatPage.tsx     # Research chat interface
│   │   ├── KnowledgeGraphPage.tsx # Graph visualization
│   │   ├── DiscoveryPage.tsx # Discovery dashboard
│   │   └── HypothesisPage.tsx # Hypothesis hub
│   ├── services/            # API services
│   │   ├── apiClient.ts     # Axios configuration
│   │   └── researchService.ts # Research API calls
│   ├── hooks/               # Custom React hooks
│   ├── types/               # TypeScript type definitions
│   └── data/                # Mock data for offline mode
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── main.py         # FastAPI application
│   │   ├── routers/        # API route handlers
│   │   ├── services/       # Business logic
│   │   ├── models/         # Database models
│   │   └── config.py      # Configuration
│   └── requirements.txt    # Python dependencies
├── public/                  # Static assets
├── index.html              # HTML entry point
├── vite.config.ts         # Vite configuration
├── tailwind.config.js     # TailwindCSS configuration
└── tsconfig.json          # TypeScript configuration
```

---

## 🛠️ Development

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

## 🔧 Configuration

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

## 📚 API Endpoints

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

## 🎨 UI Features

### Design System

- **Brutalist Design**: Bold, geometric, high-contrast interface
- **Dark Mode**: Optimized for extended research sessions
- **Responsive**: Mobile-first design, works on all devices
- **Accessible**: ARIA labels, keyboard navigation, screen reader support

### Components

- **Error Boundaries**: Graceful error handling with recovery options
- **Loading States**: Skeleton loaders and progress indicators
- **Toast Notifications**: User feedback for actions
- **Lazy Loading**: Code splitting for optimal performance

---

## 🐛 Troubleshooting

### Frontend Issues

**Blank Screen / Black Screen**
- Check browser console (F12) for errors
- Verify `node_modules` are installed: `npm install`
- Check that backend is running on port 8000
- Verify `.env` file exists with correct `VITE_API_BASE_URL`

**Build Errors**
- Clear cache: `rm -rf node_modules package-lock.json && npm install`
- Check TypeScript errors: `npm run lint`
- Verify Node.js version: `node --version` (should be 18+)

**API Connection Issues**
- Verify backend is running: `curl http://localhost:8000/health`
- Check CORS settings in backend
- Verify `VITE_API_BASE_URL` in `.env` matches backend URL

### Backend Issues

**Import Errors**
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`

**Database Errors**
- Check database connection string in `config.py`
- Verify PostgreSQL is running (if using external DB)

**Port Already in Use**
- Change port: `uvicorn app.main:app --port 8001`
- Update `VITE_API_BASE_URL` in frontend `.env`

---

## 🚢 Deployment

### Frontend Deployment

**Vercel / Netlify**
```bash
npm run build
# Deploy the `dist/` folder
```

**Docker**
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "preview"]
```

### Backend Deployment

**Docker**
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Cloud Platforms**
- **Heroku**: Use Procfile with `uvicorn app.main:app`
- **AWS**: Use Elastic Beanstalk or ECS
- **Google Cloud**: Use Cloud Run or App Engine

---

## 🧪 Testing

### Frontend Testing

```bash
# Run type checking
npm run lint

# Add tests (example with Vitest)
npm install -D vitest @testing-library/react
```

### Backend Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- **Frontend**: Follow TypeScript strict mode, use functional components
- **Backend**: Follow PEP 8, use type hints, async/await patterns
- **Commits**: Use conventional commits format

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🙏 Acknowledgments

- **React** - UI framework
- **FastAPI** - Backend framework
- **TailwindCSS** - Styling
- **Vite** - Build tool
- **TypeScript** - Type safety
- **ChromaDB** - Vector database
- **HuggingFace** - AI models

---

## 📞 Support

- **Documentation**: Check this README and inline code comments
- **Issues**: Open an issue on GitHub
- **Email**: contact@eureka.ai (placeholder)

---

## 🗺️ Roadmap

### Phase 1 (Current) ✅
- [x] Complete frontend UI
- [x] Backend API implementation
- [x] RAG functionality with HuggingFace embeddings
- [x] HuggingFace-powered discovery engine
- [x] Research gap detection
- [x] Hypothesis generation
- [x] Trend detection
- [x] Contradiction detection
- [x] Knowledge graph visualization
- [x] Discovery dashboard

### Phase 2 (Next)
- [ ] Real-time collaboration
- [ ] Advanced graph algorithms
- [ ] Mobile app
- [ ] User authentication
- [ ] File upload UI component
- [ ] Larger HuggingFace models (GPU support)

### Phase 3 (Future)
- [ ] Multi-language support
- [ ] Advanced analytics dashboard
- [ ] API rate limiting
- [ ] Caching layer
- [ ] Microservices architecture
- [ ] Custom HuggingFace model fine-tuning

---

**Built with ❤️ for researchers and scientists**

*Eureka - Discover Faster, Research Smarter* 🔬✨
