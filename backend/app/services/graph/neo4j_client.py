"""Neo4j database client."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

try:
    from neo4j import AsyncDriver, AsyncGraphDatabase
except Exception:  # pragma: no cover - exercised when optional driver is absent
    try:
        from neo4j import AsyncGraphDatabase
        AsyncDriver = object
    except Exception:
        AsyncGraphDatabase = None
        AsyncDriver = object

from app.config import get_settings

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Async Neo4j database client."""

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ):
        settings = get_settings()
        self.uri = uri or settings.NEO4J_URI
        self.user = user or settings.NEO4J_USER
        self.password = password or settings.NEO4J_PASSWORD
        self.database = database or settings.NEO4J_DATABASE
        self._driver: Optional[AsyncDriver] = None

    async def connect(self) -> None:
        """Establish connection to Neo4j."""
        if AsyncGraphDatabase is None:
            raise RuntimeError(
                "Neo4j driver is not installed. Install backend requirements or run "
                "`pip install neo4j` to enable graph-native features."
            )

        if self._driver is None:
            try:
                self._driver = AsyncGraphDatabase.driver(
                    self.uri,
                    auth=(self.user, self.password),
                )
                # Verify connection
                await self._driver.verify_connectivity()
                logger.info(f"Connected to Neo4j at {self.uri}")
            except Exception as e:
                message = str(e)
                hint = ""
                if "DNS resolve" in message or "Name or service not known" in message:
                    hint = (
                        " Check NEO4J_URI host and scheme. Aura usually requires "
                        "neo4j+s://<instance>.databases.neo4j.io"
                    )
                logger.error(f"Failed to connect to Neo4j at {self.uri}: {message}.{hint}")
                raise RuntimeError(f"Failed to connect Neo4j ({self.uri}): {message}.{hint}") from e

    async def disconnect(self) -> None:
        """Close connection to Neo4j."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            logger.info("Disconnected from Neo4j")

    async def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return results."""
        if self._driver is None:
            await self.connect()

        db = database or self.database
        results = []

        async with self._driver.session(database=db) as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            for record in records:
                results.append(dict(record))

        return results

    async def execute_write(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a write query and return result."""
        if self._driver is None:
            await self.connect()

        db = database or self.database

        async with self._driver.session(database=db) as session:
            result = await session.run(query, parameters or {})
            record = await result.single()
            return dict(record) if record else {}

    async def initialize_schema(self) -> None:
        """Create constraints and indexes."""
        from app.services.graph.queries import INIT_CONSTRAINTS

        # Split into individual statements
        statements = [
            s.strip()
            for s in INIT_CONSTRAINTS.split(";")
            if s.strip()
        ]

        for stmt in statements:
            try:
                await self.execute_write(stmt)
                logger.info(f"Created constraint: {stmt[:60]}...")
            except Exception as e:
                # Constraints may already exist
                if "AlreadyExist" not in str(e):
                    logger.warning(f"Schema init warning: {e}")

        logger.info("Neo4j schema initialization complete")

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._driver is not None


# Global client instance
_neo4j_client: Optional[Neo4jClient] = None


def get_neo4j_client() -> Neo4jClient:
    """Get or create the Neo4j client instance."""
    global _neo4j_client
    if _neo4j_client is None:
        _neo4j_client = Neo4jClient()
    return _neo4j_client
