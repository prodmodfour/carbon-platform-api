"""Add calculated estimate fields to usage samples.

Revision ID: 20260517_0002
Revises: 20260517_0001
Create Date: 2026-05-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260517_0002"
down_revision: str | Sequence[str] | None = "20260517_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add calculated estimate columns to usage samples."""
    op.add_column(
        "usage_samples",
        sa.Column(
            "normalized_usage_amount",
            sa.Numeric(18, 6),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column(
        "usage_samples",
        sa.Column(
            "normalized_usage_unit",
            sa.String(length=32),
            server_default=sa.text("'unknown'"),
            nullable=False,
        ),
    )
    op.add_column(
        "usage_samples",
        sa.Column(
            "energy_kwh",
            sa.Numeric(18, 6),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column(
        "usage_samples",
        sa.Column(
            "carbon_intensity_grams_co2e_per_kwh",
            sa.Numeric(12, 4),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column(
        "usage_samples",
        sa.Column(
            "estimated_grams_co2e",
            sa.Numeric(18, 4),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column(
        "usage_samples",
        sa.Column(
            "factor_source",
            sa.String(length=120),
            server_default=sa.text("'migration-placeholder'"),
            nullable=False,
        ),
    )

    for column_name in (
        "normalized_usage_amount",
        "normalized_usage_unit",
        "energy_kwh",
        "carbon_intensity_grams_co2e_per_kwh",
        "estimated_grams_co2e",
        "factor_source",
    ):
        op.alter_column("usage_samples", column_name, server_default=None)


def downgrade() -> None:
    """Remove calculated estimate columns from usage samples."""
    op.drop_column("usage_samples", "factor_source")
    op.drop_column("usage_samples", "estimated_grams_co2e")
    op.drop_column("usage_samples", "carbon_intensity_grams_co2e_per_kwh")
    op.drop_column("usage_samples", "energy_kwh")
    op.drop_column("usage_samples", "normalized_usage_unit")
    op.drop_column("usage_samples", "normalized_usage_amount")
