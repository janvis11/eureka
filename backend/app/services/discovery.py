"""Additional discovery endpoints.

This module contains supplementary endpoints for the discovery API.
Main discovery routes are in discovery_engine.py
"""

from fastapi import APIRouter
from app.services.discovery_engine import DiscoveryEngine
from app.services.rag_engine import RAGEngine
from app.services.knowledge_graph import KeywordExtractor
from app.services.shared import get_gateway

router = APIRouter(tags=["discovery"])

# Initialize services for report endpoint
_gateway = get_gateway()
rag_engine = RAGEngine(gateway=_gateway)
keyword_extractor = KeywordExtractor(gateway=_gateway)
discovery_engine = DiscoveryEngine(rag_engine, keyword_extractor, gateway=_gateway)


@router.get("/report")
async def get_report():
    """Get the latest research intelligence report."""
    # Access report from last discovery run
    # Note: This requires discovery to have been run first
    return {"report": "Report generation requires running /api/discovery/analyze first. Use the 'report' field from the analyze response."}
