"""Shared service singletons.

Place shared, expensive-to-initialize objects here (HF client, etc.)
so that the application reuses them across routers and services.
"""
from app.services.hf_client import HFClient


# Singleton HF client used across services
hf_client = HFClient()
