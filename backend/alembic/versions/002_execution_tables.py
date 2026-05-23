"""Add execution_runs and execution_events tables

Revision ID: 002
Revises: 001
Create Date: 2026-05-21
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── execution_runs ────────────────────────────────────────────────
    op.create_table(
        "execution_runs",
        sa.Column("id",                    sa.String(36),   primary_key=True),
        sa.Column("target_url",            sa.Text(),       nullable=False),
        sa.Column("framework",             sa.String(64),   nullable=True),
        sa.Column("status",                sa.String(32),   nullable=False, server_default="queued"),
        sa.Column("config",                sa.JSON, nullable=False, server_default="{}"),
        sa.Column("total_events",          sa.Integer(),    nullable=False, server_default="0"),
        sa.Column("findings_count",        sa.Integer(),    nullable=False, server_default="0"),
        sa.Column("blast_radius_score",    sa.Float(),      nullable=True),
        sa.Column("blast_radius_detail",   sa.JSON, nullable=True),
        sa.Column("persistence_detected",  sa.Boolean(),    nullable=False, server_default="false"),
        sa.Column("persistence_detail",    sa.JSON, nullable=True),
        sa.Column("error_message",         sa.String(1000), nullable=True),
        sa.Column("created_at",            sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at",            sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at",          sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_execution_runs_status",     "execution_runs", ["status"])
    op.create_index("ix_execution_runs_created_at", "execution_runs", ["created_at"])

    # ── execution_events ──────────────────────────────────────────────
    op.create_table(
        "execution_events",
        sa.Column("id",                 sa.String(36),   primary_key=True),
        sa.Column("run_id",             sa.String(36),
                  sa.ForeignKey("execution_runs.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("sequence",           sa.Integer(),    nullable=False),
        sa.Column("event_type",         sa.String(64),   nullable=False),
        sa.Column("node_id",            sa.String(256),  nullable=True),
        sa.Column("payload_sent",       sa.Text(),       nullable=True),
        sa.Column("response_received",  sa.Text(),       nullable=True),
        sa.Column("classification",     sa.String(32),   nullable=False, server_default="unknown"),
        sa.Column("severity",           sa.String(32),   nullable=False, server_default="info"),
        sa.Column("duration_ms",        sa.Integer(),    nullable=True),
        sa.Column("metadata",           sa.JSON, nullable=False, server_default="{}"),
        sa.Column("timestamp",          sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_execution_events_run_id",   "execution_events", ["run_id"])
    op.create_index("ix_execution_events_sequence",
                    "execution_events", ["run_id", "sequence"])
    op.create_index("ix_execution_events_type",
                    "execution_events", ["event_type"])
    op.create_index("ix_execution_events_severity",
                    "execution_events", ["severity"])


def downgrade() -> None:
    op.drop_table("execution_events")
    op.drop_table("execution_runs")
