import uvicorn
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Implemented Core modules
from core.database import db, logger
from core.config import settings
from core.postgres import engine, Base
import models.pg_models  # Ensure models are registered
from core.cache import init_semantic_cache

# APIRouters
from api.routes import ingestion, graph, risk, auth, stats

# Prometheus Instrumentation
from prometheus_fastapi_instrumentator import Instrumentator

async def create_db_constraints():
    """Create UNIQUE constraints mapping exactly to Node requirements to prevent duplicates."""
    logger.info("Verifying Neo4j Constraints...")
    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Supplier) REQUIRE s.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Part) REQUIRE p.code IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (f:Factory) REQUIRE f.name IS UNIQUE",
        "CREATE FULLTEXT INDEX supplierNameIndex IF NOT EXISTS FOR (n:Supplier) ON EACH [n.name]"
    ]
    for cypher in constraints:
        try:
            await db.execute_query(cypher)
        except Exception as e:
            logger.error(f"Failed to create constraint: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create Neo4j Constraints
    await create_db_constraints()
    
    # Startup: Create PostgreSQL Tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("PostgreSQL Tables verified/created.")
    
    # Startup: Initialize Semantic Cache
    init_semantic_cache()
    
    yield
    # Shutdown: clean up db connection
    await db.close()

app = FastAPI(
    title="N-Tier Supply Chain Intelligence API",
    description="""
    Advanced Knowledge Graph ingestion and risk analysis platform.
    
    * **Ingestion**: Automated PDF extraction and news risk assessment.
    * **Graph**: Real-time N-Tier supply chain visualization.
    * **Risk**: Recursive simulation of supply path failures and bottleneck detection.
    """,
    version="1.0.0",
    contact={
        "name": "N-Tier Intelligence Support",
        "url": "https://github.com/DoneitP1/N-Tier-Supply-Chain-Intelligence",
    },
    license_info={
        "name": "MIT License",
    },
    lifespan=lifespan
)

# Prometheus Instrumentation
Instrumentator().instrument(app).expose(app)

# CORS Middleware
# We strictly load allowed origins from settings to prevent unauthorized access.
# If allow_credentials is True, allow_origins cannot be ["*"].
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(ingestion.router)
app.include_router(graph.router)
app.include_router(risk.router)
app.include_router(stats.router)

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
