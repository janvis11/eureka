from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
try:
    from slowapi import SlowAPI, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address
except Exception:  # pragma: no cover - optional dependency in local dev
    SlowAPI = None
    _rate_limit_exceeded_handler = None
    RateLimitExceeded = None
    get_remote_address = None
from contextlib import asynccontextmanager
import logging
import sys
import time
from sqlalchemy import text

from app.routers import documents, query, discovery, graph
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


def setup_rate_limiter(app: FastAPI):
    """Configure rate limiting for API endpoints."""
    if SlowAPI is None or get_remote_address is None or RateLimitExceeded is None:
        logger.warning("Rate limiting disabled: slowapi is not installed")
        return None

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

    # Check model gateway
    try:
        from app.services.shared import get_gateway
        gateway = get_gateway()
        provider_type = type(gateway).__name__
        logger.info(f"Model gateway initialized: {provider_type}")
    except Exception as e:
        logger.error(f"Model gateway failed: {e}")

    # Log provider info
    if settings.GROQ_API_KEY:
        logger.info("Groq API key configured")
    if getattr(settings, "OPENAI_API_KEY", None):
        logger.info("OpenAI API key configured")
    if not settings.GROQ_API_KEY and not getattr(settings, "OPENAI_API_KEY", None):
        logger.warning("No LLM API keys set — using fake provider or will fail at runtime")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    # Startup
    logger.info("=" * 50)
    logger.info("Starting up Eureka AI Backend...")
    logger.info("=" * 50)

    init_db()
    logger.info("Database initialized")

    # Initialize Neo4j connection
    try:
        from app.services.graph.neo4j_client import get_neo4j_client
        neo4j_client = get_neo4j_client()
        await neo4j_client.connect()
        await neo4j_client.initialize_schema()
        logger.info("Neo4j knowledge graph initialized")
    except Exception as e:
        logger.warning(f"Neo4j not available (this is OK for development): {e}")

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
    description="Discovery platform backend — provider-agnostic RAG + Discovery",
    version="0.3.0",
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
app.include_router(graph.router, prefix="/api", tags=["graph"])


@app.get("/health")
async def health_check():
    """Health check endpoint with detailed status."""
    from app.models.database import engine

    health_status = {
        "status": "healthy",
        "service": "Eureka AI Backend",
        "version": "0.3.0",
        "checks": {
            "database": "unknown",
            "vector_store": "unknown",
            "model_gateway": "unknown",
            "knowledge_graph": "unknown"
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
        from app.services.shared import get_gateway
        rag = RAGEngine(gateway=get_gateway())
        stats = rag.get_stats()
        health_status["checks"]["vector_store"] = "healthy"
        health_status["vector_store_chunks"] = stats.get("total_chunks", 0)
    except Exception as e:
        health_status["checks"]["vector_store"] = "unhealthy"
        health_status["status"] = "degraded"
        logger.error(f"Vector store health check failed: {e}")

    # Check model gateway
    try:
        from app.services.shared import get_gateway
        gateway = get_gateway()
        health_status["checks"]["model_gateway"] = "healthy"
        health_status["model_provider"] = type(gateway).__name__
    except Exception as e:
        health_status["checks"]["model_gateway"] = "unhealthy"
        health_status["status"] = "degraded"
        logger.error(f"Model gateway health check failed: {e}")

    # Check knowledge graph (Neo4j)
    try:
        from app.services.graph.neo4j_client import get_neo4j_client
        neo4j = get_neo4j_client()
        if not neo4j.is_connected:
            await neo4j.connect()
            await neo4j.initialize_schema()

        stats = await neo4j.execute_query("MATCH (n) RETURN count(n) AS count")
        health_status["checks"]["knowledge_graph"] = "healthy"
        health_status["graph_nodes"] = stats[0].get("count", 0) if stats else 0
    except Exception as e:
        health_status["checks"]["knowledge_graph"] = "unhealthy"
        logger.warning(f"Neo4j health check failed (may not be running): {e}")

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
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": type(exc).__name__,
        },
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Eureka AI - Research Discovery Platform",
        "version": "0.3.0",
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
