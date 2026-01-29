# Re-export database models
from app.models.database import (
    Document,
    Query,
    Discovery,
    Hypothesis
)

__all__ = ["Document", "Query", "Discovery", "Hypothesis"]
