import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager

# Implemented Core modules
from core.database import db, logger
from core.config import settings

# APIRouters
from api.routes import ingestion, graph, risk, auth

# Rate Limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Initialize Rate Limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

async def create_db_constraints():
    """Create UNIQUE constraints mapping exactly to Node requirements to prevent duplicates."""
    logger.info("Verifying Neo4j Constraints...")
    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Supplier) REQUIRE s.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Part) REQUIRE p.code IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (f:Factory) REQUIRE f.name IS UNIQUE"
    ]
    for cypher in constraints:
        try:
            await db.execute_query(cypher)
        except Exception as e:
            logger.error(f"Failed to create constraint: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create Constraints
    await create_db_constraints()
    yield
    # Shutdown: clean up db connection
    await db.close()

app = FastAPI(
    title="N-Tier Supply Chain Intelligence API",
    description="Knowledge Graph ingestion and risk analysis endpoints.",
    version="1.0.0",
    lifespan=lifespan
)

# Attach Rate Limiter to FastAPI
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Include Routers
app.include_router(auth.router)
app.include_router(ingestion.router)
app.include_router(graph.router)
app.include_router(risk.router)

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
