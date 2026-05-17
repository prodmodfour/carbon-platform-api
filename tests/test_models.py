"""Tests for SQLAlchemy model metadata."""

import carbon_platform_api.models  # noqa: F401
from carbon_platform_api.db.base import Base


def test_initial_model_metadata_declares_required_tables() -> None:
    """The persistence model should include the required tables."""
    assert set(Base.metadata.tables) >= {
        "workspaces",
        "usage_samples",
        "carbon_intensity_samples",
    }


def test_usage_sample_model_declares_calculated_estimate_columns() -> None:
    """Usage sample persistence should include calculated estimate fields."""
    usage_sample_columns = set(Base.metadata.tables["usage_samples"].columns.keys())

    assert usage_sample_columns >= {
        "normalized_usage_amount",
        "normalized_usage_unit",
        "energy_kwh",
        "carbon_intensity_grams_co2e_per_kwh",
        "estimated_grams_co2e",
        "factor_source",
    }
