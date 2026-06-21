"""Fix Audit datetime columns to TIMESTAMP WITH TIME ZONE

Revision ID: 007
Revises: 006
Create Date: 2026-06-21
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for col in ("started_at", "completed_at", "created_at"):
        op.alter_column(
            "audits",
            col,
            type_=sa.DateTime(timezone=True),
            postgresql_using=f"{col} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    for col in ("started_at", "completed_at", "created_at"):
        op.alter_column(
            "audits",
            col,
            type_=sa.DateTime(timezone=False),
            postgresql_using=f"{col} AT TIME ZONE 'UTC'",
        )
