import logging
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application configuration settings using Pydantic Settings."""

    APP_NAME: str = "Precision Data Platform - Notebook Backend"
    # SEC-019: Default to "production" so docs/redoc are hidden unless explicitly enabled.
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Database Configuration
    # SEC-005: The default value contains example credentials for LOCAL DEVELOPMENT ONLY.
    # Override DATABASE_URL via environment variable before any non-development deployment.
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/precision_notebook"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 1800

    # SEC-001: API Key authentication.
    # Set API_KEY to a strong random value (e.g. `openssl rand -hex 32`).
    # REQUIRE_AUTH=False allows unauthenticated access (development/testing default).
    # Set REQUIRE_AUTH=True in production to enforce API key validation on all routes.
    API_KEY: str = ""
    REQUIRE_AUTH: bool = False

    # SEC-002: Credential encryption key for Fernet symmetric encryption.
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # If empty, credentials are stored as plaintext with a startup warning (development fallback).
    CREDENTIAL_ENCRYPTION_KEY: str = ""

    # SEC-007: CORS — comma-separated list of allowed origins.
    # Default allows localhost for development. Override in production.
    CORS_ALLOW_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
