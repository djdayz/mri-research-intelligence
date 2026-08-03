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
    database_pool_size: int = Field(
        default=5,
        ge=1,
    )
    database_max_overflow: int = Field(
        default=10,
        ge=0,
    )
    database_pool_timeout_seconds: float = Field(
        default=30.0,
        gt=0,
    )
    database_pool_recycle_seconds: int = Field(
        default=1800,
        ge=1,
    )

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

    pdf_max_bytes: int = Field(
        default=25 * 1024 * 1024,
        ge=1,
    )

    pdf_max_pages: int = Field(
        default=500,
        ge=1,
    )

    llm_provider: Literal["unconfigured", "fake", "openai"] = "unconfigured"
    llm_api_key: str | None = None
    llm_model: str = "gpt-5.6"
    llm_timeout_seconds: float = Field(
        default=45.0,
        gt=0,
    )
    llm_max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
    )
    llm_prompt_budget_tokens: int = Field(
        default=1600,
        ge=1,
    )

    digest_delivery_provider: Literal["file", "console", "smtp"] = "file"
    digest_delivery_retry_delay_seconds: int = Field(
        default=900,
        ge=0,
    )

    smtp_host: str | None = None
    smtp_port: int = Field(
        default=587,
        ge=1,
        le=65535,
    )
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_sender: str | None = None
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    smtp_timeout_seconds: float = Field(
        default=10.0,
        gt=0,
    )
    smtp_max_attempts: int = Field(
        default=3,
        ge=1,
        le=5,
    )
    smtp_backoff_seconds: float = Field(
        default=0.5,
        ge=0,
    )


@lru_cache
def get_settings() -> Settings:
    """Return one cached settings instance for the application process"""

    return Settings()  # type: ignore[call-arg]
