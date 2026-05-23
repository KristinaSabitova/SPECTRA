"""Add is_temporary_password to users

Revision ID: 003
Revises: 002
Create Date: 2026-05-22
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('is_temporary_password', sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column('users', 'is_temporary_password')
