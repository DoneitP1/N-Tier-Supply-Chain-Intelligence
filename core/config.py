from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Central configuration management for N-Tier Supply Chain."""
    
    # Neo4j Database
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    
    # LLM APIs
    anthropic_api_key: str = ""
    google_api_key: str = ""
    
    # Application Security
    app_api_key: str = "super_secret_dev_key"
    secret_key: str = "a_very_secret_key_change_me_in_production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Use pydantic-settings v2 config style to load from .env automatically
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

# Initialize and export singleton instance
settings = Settings()
