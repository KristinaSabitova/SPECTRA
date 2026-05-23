"""
Event bus for real-time execution tracing.

Each ExecutionRun has a set of subscriber queues. The runner publishes
EngineEvents; the SSE endpoint consumes them per-run.
"""

from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EventType(str, Enum):
    run_started       = "run_started"
    recon_started     = "recon_started"
    recon_completed   = "recon_completed"
    probe_sent        = "probe_sent"
    response_received = "response_received"
    payload_injected  = "payload_injected"
    tool_detected     = "tool_detected"
    finding_generated = "finding_generated"
    blast_computed    = "blast_computed"
    persistence_check = "persistence_check"
    run_completed     = "run_completed"
    error             = "error"


class Classification(str, Enum):
    benign     = "benign"
    suspicious = "suspicious"
    malicious  = "malicious"
    unknown    = "unknown"


class Severity(str, Enum):
    critical = "critical"
    high     = "high"
    medium   = "medium"
    low      = "low"
    info     = "info"


@dataclass
class EngineEvent:
    run_id:         str
    event_type:     EventType
    sequence:       int
    node_id:        str | None         = None
    payload_sent:   str | None         = None
    response_received: str | None      = None
    classification: Classification     = Classification.unknown
    severity:       Severity           = Severity.info
    duration_ms:    int | None         = None
    metadata:       dict[str, Any]     = field(default_factory=dict)
    timestamp:      datetime           = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_sse(self) -> str:
        """Serialize to SSE data line."""
        import json
        data = {
            "id":               self.id,
            "run_id":           self.run_id,
            "event_type":       self.event_type,
            "sequence":         self.sequence,
            "node_id":          self.node_id,
            "payload_sent":     self.payload_sent,
            "response_received": self.response_received,
            "classification":   self.classification,
            "severity":         self.severity,
            "duration_ms":      self.duration_ms,
            "metadata":         self.metadata,
            "timestamp":        self.timestamp.isoformat(),
        }
        return f"data: {json.dumps(data)}\n\n"


_SENTINEL = object()


class EventBus:
    """Thread-safe async event bus keyed by run_id."""

    def __init__(self) -> None:
        self._subs: dict[str, list[asyncio.Queue]] = defaultdict(list)

    def subscribe(self, run_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=1024)
        self._subs[run_id].append(q)
        return q

    async def publish(self, event: EngineEvent) -> None:
        for q in self._subs[event.run_id]:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass  # slow consumer — drop rather than block the runner

    async def close(self, run_id: str) -> None:
        """Send sentinel to all subscribers so they know the run is done."""
        for q in self._subs[run_id]:
            try:
                q.put_nowait(_SENTINEL)
            except asyncio.QueueFull:
                pass
        self._subs.pop(run_id, None)

    def unsubscribe(self, run_id: str, q: asyncio.Queue) -> None:
        try:
            self._subs[run_id].remove(q)
        except (ValueError, KeyError):
            pass

    @staticmethod
    def is_sentinel(obj: Any) -> bool:
        return obj is _SENTINEL


# Module-level singleton — shared across the process
event_bus: EventBus = EventBus()
