from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Central configuration management for N-Tier Supply Chain."""
    
    # Neo4j Database
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    
    # PostgreSQL Database
    postgres_url: str = "postgresql+asyncpg://user:password@localhost:5432/ntier"
    
    # Redis and Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    
    # LLM APIs
    anthropic_api_key: str = ""
    google_api_key: str = ""
    
    # Application Security
    app_api_key: str = "dev_key_only" # MUST be overridden in production
    secret_key: str = "dev_secret_only" # MUST be overridden in production
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    max_upload_size_mb: int = 10
    
    # CORS
    allowed_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # Use pydantic-settings v2 config style to load from .env automatically
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

# Initialize and export singleton instance
settings = Settings()
