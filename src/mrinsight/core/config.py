from functools import lru_cache
from typing import Literal

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


@lru_cache
def get_settings() -> Settings:
    """Return one cached settings instance for the application process"""

    return Settings()
