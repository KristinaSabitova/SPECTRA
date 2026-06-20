"""Add owner_id to pipelines for cross-tenant isolation

Revision ID: 006
Revises: 005
Create Date: 2026-06-21
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("pipelines") as batch_op:
        batch_op.add_column(
            sa.Column(
                "owner_id",
                sa.String(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            )
        )
        batch_op.create_index("ix_pipelines_owner_id", ["owner_id"])


def downgrade() -> None:
    with op.batch_alter_table("pipelines") as batch_op:
        batch_op.drop_index("ix_pipelines_owner_id")
        batch_op.drop_column("owner_id")
