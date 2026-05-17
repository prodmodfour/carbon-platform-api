"""Application configuration loaded from environment variables."""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ALLOWED_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}


class Settings(BaseSettings):
    """Runtime settings for the API.

    Environment variables use the ``CARBON_API_`` prefix, for example
    ``CARBON_API_LOG_LEVEL=DEBUG``.
    """

    model_config = SettingsConfigDict(env_prefix="CARBON_API_", extra="ignore")

    app_name: str = "carbon-platform-api"
    app_version: str = "0.1.0"
    environment: str = "local"
    log_level: str = "INFO"
    docs_enabled: bool = False
    database_url: str = (
        "postgresql+asyncpg://carbon_platform_api:local_dev_password"
        "@localhost:5432/carbon_platform_api"
    )

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        """Normalize and validate standard library log level names."""
        normalized_value = value.upper()
        if normalized_value not in _ALLOWED_LOG_LEVELS:
            allowed_values = ", ".join(sorted(_ALLOWED_LOG_LEVELS))
            raise ValueError(f"log_level must be one of: {allowed_values}")
        return normalized_value


def get_settings() -> Settings:
    """Load settings from the current process environment."""
    return Settings()
