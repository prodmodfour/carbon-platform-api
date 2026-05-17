"""Application configuration loaded from environment variables."""

from pydantic import Field, field_validator
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
    redis_url: str = "redis://localhost:6379/0"
    carbon_intensity_provider_base_url: str = "https://carbon-intensity.example.invalid"
    carbon_intensity_provider_timeout_seconds: float = Field(default=2.0, gt=0)
    carbon_intensity_cache_ttl_seconds: int = Field(default=900, gt=0)

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        """Normalize and validate standard library log level names."""
        normalized_value = value.upper()
        if normalized_value not in _ALLOWED_LOG_LEVELS:
            allowed_values = ", ".join(sorted(_ALLOWED_LOG_LEVELS))
            raise ValueError(f"log_level must be one of: {allowed_values}")
        return normalized_value

    @field_validator("redis_url", "carbon_intensity_provider_base_url")
    @classmethod
    def strip_and_validate_url_like_setting(cls, value: str) -> str:
        """Trim URL-like settings and reject whitespace-only values."""
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("URL-like settings must not be blank")
        return stripped_value


def get_settings() -> Settings:
    """Load settings from the current process environment."""
    return Settings()
