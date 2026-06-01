"""Shared service singletons.

Provides the global ModelGateway instance used across routers and services.
"""

from app.services.model_gateway import ModelGateway, create_gateway
import logging

logger = logging.getLogger(__name__)


class GatewaySingleton:
    """Lazy-loading singleton for the model gateway."""
    _instance = None

    @classmethod
    def get_instance(cls) -> ModelGateway:
        if cls._instance is None:
            try:
                cls._instance = create_gateway()
                logger.info("ModelGateway singleton initialized")
            except Exception as e:
                logger.error(f"Failed to initialize ModelGateway singleton: {e}")
                raise
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset singleton (useful in tests)."""
        cls._instance = None


def get_gateway() -> ModelGateway:
    """Get the shared model gateway instance."""
    return GatewaySingleton.get_instance()
