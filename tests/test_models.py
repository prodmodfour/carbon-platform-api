"""Tests for SQLAlchemy model metadata."""

import carbon_platform_api.models  # noqa: F401
from carbon_platform_api.db.base import Base


def test_initial_model_metadata_declares_required_tables() -> None:
    """The initial persistence model should include the required T004 tables."""
    assert set(Base.metadata.tables) >= {
        "workspaces",
        "usage_samples",
        "carbon_intensity_samples",
    }
