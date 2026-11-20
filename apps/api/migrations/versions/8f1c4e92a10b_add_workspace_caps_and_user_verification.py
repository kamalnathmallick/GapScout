"""add_workspace_caps_and_user_verification

Revision ID: 8f1c4e92a10b
Revises: 01ba234950a3
Create Date: 2026-11-20 09:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8f1c4e92a10b"
down_revision: str | None = "01ba234950a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add workspace caps and retention settings
    op.add_column(
        "workspaces",
        sa.Column("max_cells_per_job", sa.Integer(), server_default=sa.text("250"), nullable=False),
    )
    op.add_column(
        "workspaces",
        sa.Column(
            "max_places_per_job", sa.Integer(), server_default=sa.text("5000"), nullable=False
        ),
    )
    op.add_column(
        "workspaces",
        sa.Column(
            "daily_llm_cost_cap_usd", sa.Float(), server_default=sa.text("2.0"), nullable=False
        ),
    )
    op.add_column(
        "workspaces",
        sa.Column(
            "data_retention_days", sa.Integer(), server_default=sa.text("90"), nullable=False
        ),
    )

    # Add user verification and password reset columns
    op.add_column(
        "users",
        sa.Column("is_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column("users", sa.Column("verification_token", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("reset_token", sa.String(length=255), nullable=True))
    op.add_column(
        "users", sa.Column("reset_token_expires_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("users", "reset_token_expires_at")
    op.drop_column("users", "reset_token")
    op.drop_column("users", "verification_token")
    op.drop_column("users", "is_verified")
    op.drop_column("workspaces", "data_retention_days")
    op.drop_column("workspaces", "daily_llm_cost_cap_usd")
    op.drop_column("workspaces", "max_places_per_job")
    op.drop_column("workspaces", "max_cells_per_job")
