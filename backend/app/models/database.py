from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)

settings = get_settings()
DATABASE_URL = settings.DATABASE_URL or "sqlite:///./eureka.db"

# Create engine with production-ready connection pooling
connect_args = {}
engine_kwargs = {
    "echo": settings.DEBUG,  # Log SQL queries in debug mode
    "pool_pre_ping": True,   # Enable connection health checks
    "pool_recycle": 3600,    # Recycle connections after 1 hour
}

if "sqlite" in DATABASE_URL:
    connect_args["check_same_thread"] = False
    # SQLite doesn't use connection pooling
    engine_kwargs.pop("pool_pre_ping", None)
    engine_kwargs.pop("pool_recycle", None)
elif "postgresql" in DATABASE_URL:
    connect_args.update({
        "pool_size": 20,
        "max_overflow": 10,
    })

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs
)

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Get database session with proper error handling."""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")


class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    file_path = Column(String, unique=True)
    source = Column(String, default="uploaded")
    upload_date = Column(DateTime, default=datetime.now)
    processing_status = Column(String, default="pending")  # pending, processing, completed, failed
    chunk_count = Column(Integer, default=0)
    doc_metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Query(Base):
    __tablename__ = "queries"
    
    id = Column(Integer, primary_key=True, index=True)
    query_text = Column(Text, nullable=False)
    response = Column(Text)
    sources = Column(JSON, default=[])
    timestamp = Column(DateTime, default=datetime.now)
    response_time = Column(Integer, default=0)  # in milliseconds


class Discovery(Base):
    __tablename__ = "discoveries"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_type = Column(String, default="full")
    gaps = Column(JSON, default=[])
    hypotheses = Column(JSON, default=[])
    contradictions = Column(JSON, default=[])
    trends = Column(JSON, default=[])
    doc_metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Hypothesis(Base):
    __tablename__ = "hypotheses"
    
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String)
    rationale = Column(Text)
    methodology = Column(Text)
    confidence = Column(Integer, default=0)
    gap_reference = Column(String)
    created_at = Column(DateTime, default=datetime.now)
