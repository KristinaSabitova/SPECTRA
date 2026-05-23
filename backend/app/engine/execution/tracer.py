"""
Execution tracer.

Persists EngineEvents to the execution_events table and
re-publishes them on the EventBus for SSE consumers.
"""
from __future__ import annotations

import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.events import EngineEvent, EventType, EventBus, event_bus
from app.models.execution import ExecutionEvent, ExecutionRun, RunStatus


class ExecutionTracer:
    """
    Manages the lifecycle of an ExecutionRun and its events.

    All events are:
      1. Inserted into execution_events
      2. Published on the EventBus for real-time SSE streaming
    """

    def __init__(self, run_id: str, db: AsyncSession):
        self.run_id   = run_id
        self.db       = db
        self._seq     = 0
        self._bus     = event_bus
        self._t_start = time.monotonic()

    # ── Event emission ────────────────────────────────────────────────

    async def emit(
        self,
        event_type: EventType,
        *,
        node_id:           str | None = None,
        payload_sent:      str | None = None,
        response_received: str | None = None,
        classification:    str        = "unknown",
        severity:          str        = "info",
        duration_ms:       int | None = None,
        metadata:          dict | None = None,
    ) -> EngineEvent:
        self._seq += 1
        event = EngineEvent(
            run_id=self.run_id,
            event_type=event_type,
            sequence=self._seq,
            node_id=node_id,
            payload_sent=payload_sent,
            response_received=response_received,
            classification=classification,  # type: ignore[arg-type]
            severity=severity,              # type: ignore[arg-type]
            duration_ms=duration_ms,
            metadata=metadata or {},
        )
        # Persist
        db_event = ExecutionEvent(
            id=event.id,
            run_id=event.run_id,
            sequence=event.sequence,
            event_type=event.event_type,
            node_id=event.node_id,
            payload_sent=event.payload_sent,
            response_received=event.response_received,
            classification=event.classification,
            severity=event.severity,
            duration_ms=event.duration_ms,
            event_metadata=event.metadata,
            timestamp=event.timestamp,
        )
        self.db.add(db_event)
        await self.db.flush()

        # Publish to SSE bus (non-blocking)
        await self._bus.publish(event)
        return event

    # ── Run lifecycle ─────────────────────────────────────────────────

    async def start_run(self) -> None:
        from datetime import datetime, timezone
        run = await self._get_run()
        run.status     = RunStatus.running
        run.started_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.emit(EventType.run_started, metadata={"run_id": self.run_id})

    async def complete_run(
        self,
        *,
        findings_count:      int   = 0,
        blast_radius_score:  float | None = None,
        blast_radius_detail: dict  | None = None,
        persistence_detected: bool        = False,
        persistence_detail:  dict  | None = None,
    ) -> None:
        from datetime import datetime, timezone
        run = await self._get_run()
        run.status                = RunStatus.completed
        run.completed_at          = datetime.now(timezone.utc)
        run.total_events          = self._seq
        run.findings_count        = findings_count
        run.blast_radius_score    = blast_radius_score
        run.blast_radius_detail   = blast_radius_detail
        run.persistence_detected  = persistence_detected
        run.persistence_detail    = persistence_detail
        await self.db.flush()
        await self.emit(
            EventType.run_completed,
            metadata={
                "findings_count":       findings_count,
                "blast_radius_score":   blast_radius_score,
                "persistence_detected": persistence_detected,
                "elapsed_ms": int((time.monotonic() - self._t_start) * 1000),
            },
        )
        await self._bus.close(self.run_id)

    async def fail_run(self, error: str) -> None:
        from datetime import datetime, timezone
        run = await self._get_run()
        run.status        = RunStatus.failed
        run.completed_at  = datetime.now(timezone.utc)
        run.total_events  = self._seq
        run.error_message = error[:1000]
        await self.db.flush()
        await self.emit(EventType.error, severity="critical", metadata={"error": error})
        await self._bus.close(self.run_id)

    # ── Private ───────────────────────────────────────────────────────

    async def _get_run(self) -> ExecutionRun:
        from sqlalchemy import select
        result = await self.db.execute(
            select(ExecutionRun).where(ExecutionRun.id == self.run_id)
        )
        run = result.scalar_one()
        return run
