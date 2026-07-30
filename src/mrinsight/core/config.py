from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration from environment variables"""

    model_config = SettingsConfigDict(
        # Maps to MRINSIGHT_SERVICE_NAME, MRINSIGHT_APP_NAME, etc.
        env_prefix="MRINSIGHT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    service_name: str = "mrinsight"
    app_name: str = "MRInsight"
    environment: Literal["local", "test", "staging", "production"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    database_url: str
    test_database_url: str | None = None

    crossref_mailto: str | None = None
    crossref_base_url: str = "https://api.crossref.org"
    crossref_user_agent: str = "MRInsight/0.1"

    crossref_timeout_seconds: float = Field(
        default=10.0,
        gt=0,
    )

    crossref_connect_timeout_seconds: float = Field(
        default=5.0,
        gt=0,
    )

    crossref_max_attempts: int = Field(
        default=3,
        ge=1,
        le=5,
    )

    crossref_backoff_seconds: float = Field(
        default=0.5,
        ge=0,
    )


@lru_cache
def get_settings() -> Settings:
    """Return one cached settings instance for the application process"""

    return Settings()  # type: ignore[call-arg]
