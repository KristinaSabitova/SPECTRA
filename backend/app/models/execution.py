import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class RunStatus(str, Enum):
    queued    = "queued"
    running   = "running"
    completed = "completed"
    failed    = "failed"
    cancelled = "cancelled"


class ExecutionRun(Base):
    __tablename__ = "execution_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    # Owner of this run — nullable to support pre-migration rows
    user_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    audit_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("audits.id", ondelete="SET NULL")
    )
    pipeline_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("pipelines.id", ondelete="SET NULL")
    )
    target_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    framework: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default=RunStatus.queued)
    config: Mapped[dict | None] = mapped_column(JSON)
    total_events: Mapped[int] = mapped_column(Integer, default=0)
    findings_count: Mapped[int] = mapped_column(Integer, default=0)
    blast_radius_score: Mapped[float | None] = mapped_column(Float)
    persistence_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    blast_radius_detail: Mapped[dict | None] = mapped_column(JSON)
    persistence_detail: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # TTL: job in app/tasks/cleanup.py purges rows after this timestamp
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class ExecutionEvent(Base):
    __tablename__ = "execution_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("execution_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    node_id: Mapped[str | None] = mapped_column(String(255))
    payload_sent: Mapped[str | None] = mapped_column(Text)
    response_received: Mapped[str | None] = mapped_column(Text)
    # benign | suspicious | malicious | unknown
    classification: Mapped[str] = mapped_column(String(20), default="unknown")
    # critical | high | medium | low | info
    severity: Mapped[str] = mapped_column(String(20), default="info")
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    event_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, server_default='{}')
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
