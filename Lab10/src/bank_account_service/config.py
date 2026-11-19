"""Application configuration from environment variables / .env (12-factor)."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All settings can be overridden by environment variables of the same name.

    Secrets (API_KEY) have no default and are never logged: ``SecretStr`` hides
    the value in ``repr()`` and in tracebacks.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Bank Account Service"
    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///bank.db"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    api_key: SecretStr | None = Field(default=None, description="X-API-Key for admin endpoints")
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    overview_concurrency: int = Field(default=4, ge=1, le=64)
    overview_timeout: float = Field(default=5.0, gt=0)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Settings are read once per process (cache is cleared in tests)."""
    return Settings()
