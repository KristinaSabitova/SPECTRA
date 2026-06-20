"""Add TOTP pending enrollment columns to users

Revision ID: 005
Revises: 004
Create Date: 2026-06-20
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("totp_pending_secret_enc", sa.String(512), nullable=True)
        )
        batch_op.add_column(
            sa.Column("totp_pending_expires_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("totp_pending_expires_at")
        batch_op.drop_column("totp_pending_secret_enc")
