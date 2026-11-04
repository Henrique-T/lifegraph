"""Environment-backed application configuration."""

from functools import lru_cache

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or a local .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8100
    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str
    ref_base_url: AnyHttpUrl = "http://host.docker.internal:8000"
    ref_bearer_token: str | None = None
    gliner_base_url: AnyHttpUrl = "http://gliner:8200"
    gliner_timeout_seconds: float = 120.0
    ollama_base_url: AnyHttpUrl = "http://host.docker.internal:11434"


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()
