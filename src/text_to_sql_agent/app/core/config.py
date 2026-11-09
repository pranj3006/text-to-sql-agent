"""
Central application configuration.
Single source of truth for all env-driven settings - never read os.environ
anywhere else in the codebase, import `settings` from here instead.
"""
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    APP_NAME: str = "enterprise-agent-platform"
    APP_ENV: Literal["local", "dev", "staging", "prod"] = "local"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # --- Postgres ---
    DATABASE_URL: str
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_ECHO: bool = False

    # # --- Redis ---
    # REDIS_HOST: str = "redis"
    # REDIS_PORT: int = 6379
    # REDIS_PASSWORD: str | None = None
    # REDIS_DB_CACHE: int = 0
    # REDIS_DB_CELERY_BROKER: int = 1
    # REDIS_DB_CELERY_BACKEND: int = 2
    # REDIS_DB_PUBSUB: int = 3
    # CACHE_DEFAULT_TTL_SECONDS: int = 300

    # # --- Azure AD / Entra ID ---
    # AZURE_TENANT_ID: str
    # AZURE_CLIENT_ID: str
    # AZURE_CLIENT_SECRET: str
    # AZURE_AUDIENCE: str
    # AZURE_ISSUER: str
    # AZURE_JWKS_URL: str

    # --- Azure OpenAI ---
    # AZURE_OPENAI_ENDPOINT: str
    OPENAI_API_KEY: str
    # AZURE_OPENAI_API_VERSION: str = "2024-06-01"
    # AZURE_OPENAI_CHAT_DEPLOYMENT: str
    # AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str

    # --- Observability ---
    OTEL_SERVICE_NAME: str = APP_NAME
    OTEL_ENABLED: bool = True
    OTEL_EXPORTER: Literal["console", "otlp"] = "console"
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "/var/log/app"
    LOG_JSON: bool = True

    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: str = "1536"

    # # --- MCP ---
    # MCP_FILESYSTEM_ROOT: str = "/data/mcp-fs"

    @property
    def redis_url_cache(self) -> str:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB_CACHE}"

    @property
    def redis_url_pubsub(self) -> str:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB_PUBSUB}"

    @property
    def celery_broker_url(self) -> str:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB_CELERY_BROKER}"

    @property
    def celery_result_backend(self) -> str:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB_CELERY_BACKEND}"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton - import this, don't instantiate Settings() directly."""
    return Settings()


settings = get_settings()
