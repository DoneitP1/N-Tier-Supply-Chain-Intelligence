from neo4j import AsyncGraphDatabase
import logging

class Neo4jConnection:
    """Singleton-style database connection manager."""
    def __init__(self, uri, user, pwd):
        # Using async driver for FastAPI compatibility and performance
        self._driver = AsyncGraphDatabase.driver(uri, auth=(user, pwd))
    
    async def close(self):
        if self._driver is not None:
            await self._driver.close()
    
    async def execute_query(self, query, parameters=None):
        """Standardized method to execute write/read queries."""
        async with self._driver.session() as session:
            result = await session.run(query, parameters)
            return await result.data()

def get_logger(name: str) -> logging.Logger:
    """Provides a configured logger for the application."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s")
    return logging.getLogger(name)

logger = get_logger("ntier_backend")

# Inject credentials from config
from core.config import settings
db = Neo4jConnection(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
