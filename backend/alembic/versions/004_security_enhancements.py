"""Security enhancements: user_id ownership, expires_at TTL, is_temporary_password

Revision ID: 004
Revises: 003
Create Date: 2026-06-01
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add user_id ownership to execution_runs so we can enforce per-user access
    with op.batch_alter_table("execution_runs") as batch_op:
        batch_op.add_column(
            sa.Column("user_id", sa.String(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.create_index("ix_execution_runs_user_id", ["user_id"])
        batch_op.create_index("ix_execution_runs_expires_at", ["expires_at"])
        batch_op.create_foreign_key(
            "fk_execution_runs_user_id",
            "users",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("execution_runs") as batch_op:
        batch_op.drop_constraint("fk_execution_runs_user_id", type_="foreignkey")
        batch_op.drop_index("ix_execution_runs_expires_at")
        batch_op.drop_index("ix_execution_runs_user_id")
        batch_op.drop_column("expires_at")
        batch_op.drop_column("user_id")
