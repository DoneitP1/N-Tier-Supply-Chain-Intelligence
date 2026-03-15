from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from core.config import settings

# Create async engine for PostgreSQL
engine = create_async_engine(settings.postgres_url, echo=False)

# Create async session factory
async_session = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

async def get_db():
    """Dependency for providing a database session to FastAPI routes."""
    async with async_session() as session:
        yield session
