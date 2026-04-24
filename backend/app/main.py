from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import SlowAPI, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from contextlib import asynccontextmanager
import logging
import sys
import time
from sqlalchemy import text

from app.routers import documents, query, discovery
from app.models.database import init_db
from app.config import get_settings

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Set logging levels for dependencies
logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
logging.getLogger("transformers").setLevel(logging.ERROR)


def setup_rate_limiter(app: FastAPI):
    """Configure rate limiting for API endpoints."""
    try:
        limiter = SlowAPI(
            key_func=get_remote_address,
            default_limits=["100/minute", "1000/hour"]
        )
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        return limiter
    except Exception as e:
        logger.warning(f"Rate limiting not available: {e}")
        return None


def check_dependencies():
    """Verify critical dependencies are available."""
    settings = get_settings()
    logger.info("Checking dependencies...")

    # Check embedding model
    try:
        from app.services.shared import hf_client
        hf_client.embed_text("test")
        logger.info("Embedding model loaded successfully")
    except Exception as e:
        logger.error(f"Embedding model failed: {e}")

    # Warn if GROQ API key not set
    if not settings.GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not set - LLM generation will fall back to local models")
    else:
        logger.info("GROQ API key configured")

    # Warn if HF API token not set
    if not settings.HF_API_TOKEN:
        logger.info("HF_API_TOKEN not set - using local models only")
    else:
        logger.info("HuggingFace API token configured")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    # Startup
    logger.info("=" * 50)
    logger.info("Starting up Eureka AI Backend...")
    logger.info("=" * 50)

    init_db()
    logger.info("Database initialized")

    check_dependencies()

    # Setup rate limiter
    limiter = setup_rate_limiter(app)
    if limiter:
        logger.info("Rate limiting enabled: 100/minute, 1000/hour")

    logger.info("=" * 50)
    logger.info("Eureka AI Backend ready")
    logger.info("=" * 50)

    yield

    # Shutdown
    logger.info("Shutting down Eureka AI Backend...")


# Create FastAPI app
app = FastAPI(
    title="Eureka AI Backend",
    description="Simple RAG + Discovery backend for research papers",
    version="0.2.0",
    lifespan=lifespan
)

# Add CORS middleware (configure allowed origins for production)
settings = get_settings()

# In production (DEBUG=False), restrict CORS to specific origins
if settings.DEBUG:
    allowed_origins = settings.ALLOWED_ORIGINS.split(",") if settings.ALLOWED_ORIGINS else ["*"]
else:
    # Production: only allow explicitly configured origins
    allowed_origins = [
        origin.strip()
        for origin in (settings.ALLOWED_ORIGINS.split(",") if settings.ALLOWED_ORIGINS else [])
        if origin.strip() and origin.strip() != "*"
    ]
    if not allowed_origins:
        logger.warning("DEBUG=False but no ALLOWED_ORIGINS configured - CORS will allow all origins")
        allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)
logger.info(f"CORS configured with origins: {allowed_origins}")

# Add security middleware - trusted hosts for production
if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS.split(",") if settings.ALLOWED_HOSTS else ["localhost", "127.0.0.1"]
    )
    logger.info("TrustedHostMiddleware enabled for production")

# Include routers
app.include_router(documents.router, prefix="/api", tags=["documents"])
app.include_router(query.router, prefix="/api", tags=["queries"])
app.include_router(discovery.router, prefix="/api", tags=["discovery"])


@app.get("/health")
async def health_check():
    """Health check endpoint with detailed status."""
    from app.models.database import engine

    health_status = {
        "status": "healthy",
        "service": "Eureka AI Backend",
        "version": "0.2.0",
        "checks": {
            "database": "unknown",
            "vector_store": "unknown"
        }
    }

    # Check database
    try:
        from app.models.database import engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health_status["checks"]["database"] = "healthy"
    except Exception as e:
        health_status["checks"]["database"] = "unhealthy"
        health_status["status"] = "degraded"
        logger.error(f"Database health check failed: {e}")

    # Check vector store
    try:
        from app.services.rag_engine import RAGEngine
        from app.services.shared import hf_client as shared_hf_client
        rag = RAGEngine(hf_client=shared_hf_client)
        stats = rag.get_stats()
        health_status["checks"]["vector_store"] = "healthy"
        health_status["vector_store_chunks"] = stats.get("total_chunks", 0)
    except Exception as e:
        health_status["checks"]["vector_store"] = "unhealthy"
        health_status["status"] = "degraded"
        logger.error(f"Vector store health check failed: {e}")

    return health_status


@app.get("/ready")
async def readiness_check():
    """Readiness probe for Kubernetes/docker-compose."""
    return {"ready": True}


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add request processing time header and log requests."""
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.3f}"
        logger.debug(f"{request.method} {request.url.path} - {process_time:.3f}s")
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"{request.method} {request.url.path} - Error after {process_time:.3f}s: {e}")
        raise


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception in {request.method} {request.url.path}: {exc}", exc_info=True)
    return {
        "detail": "Internal server error",
        "type": type(exc).__name__
    }, 500


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Eureka AI - Research Paper Analysis Platform",
        "version": "0.2.0",
        "endpoints": {
            "health": "/health",
            "documents": "/api/documents",
            "queries": "/api/queries",
            "discovery": "/api/discovery"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
