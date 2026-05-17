"""Create initial persistence schema.

Revision ID: 20260517_0001
Revises:
Create Date: 2026-05-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260517_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create initial database tables."""
    op.create_table(
        "workspaces",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workspaces")),
        sa.UniqueConstraint("name", name=op.f("uq_workspaces_name")),
    )

    op.create_table(
        "carbon_intensity_samples",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("region", sa.String(length=64), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("grams_co2e_per_kwh", sa.Numeric(12, 4), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_carbon_intensity_samples")),
    )
    op.create_index(
        op.f("ix_carbon_intensity_samples_measured_at"),
        "carbon_intensity_samples",
        ["measured_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_carbon_intensity_samples_region"),
        "carbon_intensity_samples",
        ["region"],
        unique=False,
    )

    op.create_table(
        "usage_samples",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("region", sa.String(length=64), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("usage_amount", sa.Numeric(18, 6), nullable=False),
        sa.Column("usage_unit", sa.String(length=32), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_usage_samples_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_usage_samples")),
    )
    op.create_index(
        op.f("ix_usage_samples_workspace_id"),
        "usage_samples",
        ["workspace_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop initial database tables."""
    op.drop_index(op.f("ix_usage_samples_workspace_id"), table_name="usage_samples")
    op.drop_table("usage_samples")
    op.drop_index(
        op.f("ix_carbon_intensity_samples_region"),
        table_name="carbon_intensity_samples",
    )
    op.drop_index(
        op.f("ix_carbon_intensity_samples_measured_at"),
        table_name="carbon_intensity_samples",
    )
    op.drop_table("carbon_intensity_samples")
    op.drop_table("workspaces")
