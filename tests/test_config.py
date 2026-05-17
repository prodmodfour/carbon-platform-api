"""Tests for environment-backed application settings."""

import pytest

from carbon_platform_api.config import Settings

_SETTINGS_ENV_VARS = (
    "CARBON_API_APP_NAME",
    "CARBON_API_APP_VERSION",
    "CARBON_API_ENVIRONMENT",
    "CARBON_API_LOG_LEVEL",
    "CARBON_API_DOCS_ENABLED",
    "CARBON_API_DATABASE_URL",
)


@pytest.fixture()
def clean_settings_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove app settings from the test process environment."""
    for env_var in _SETTINGS_ENV_VARS:
        monkeypatch.delenv(env_var, raising=False)


def test_settings_defaults(clean_settings_env: None) -> None:
    """Settings should have safe local defaults."""
    settings = Settings()

    assert settings.app_name == "carbon-platform-api"
    assert settings.app_version == "0.1.0"
    assert settings.environment == "local"
    assert settings.log_level == "INFO"
    assert settings.docs_enabled is False
    assert settings.database_url == (
        "postgresql+asyncpg://carbon_platform_api:local_dev_password"
        "@localhost:5432/carbon_platform_api"
    )


def test_settings_environment_overrides(
    clean_settings_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Settings should load environment variables with the CARBON_API_ prefix."""
    monkeypatch.setenv("CARBON_API_APP_NAME", "custom-carbon-api")
    monkeypatch.setenv("CARBON_API_APP_VERSION", "9.8.7")
    monkeypatch.setenv("CARBON_API_ENVIRONMENT", "test")
    monkeypatch.setenv("CARBON_API_LOG_LEVEL", "debug")
    monkeypatch.setenv("CARBON_API_DOCS_ENABLED", "true")
    monkeypatch.setenv(
        "CARBON_API_DATABASE_URL",
        "postgresql+asyncpg://user:pass@db.example.invalid:5432/app",
    )

    settings = Settings()

    assert settings.app_name == "custom-carbon-api"
    assert settings.app_version == "9.8.7"
    assert settings.environment == "test"
    assert settings.log_level == "DEBUG"
    assert settings.docs_enabled is True
    assert settings.database_url == (
        "postgresql+asyncpg://user:pass@db.example.invalid:5432/app"
    )
