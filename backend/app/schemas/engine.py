"""
Pydantic schemas for the engine API.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.engine.payloads.catalog import PayloadType
from app.engine.payloads.mutator import MutationStrategy
from app.models.execution import RunStatus


# ── Request schemas ───────────────────────────────────────────────────────────

class CreateRunRequest(BaseModel):
    target_url:          str = Field(..., description="URL of the target AI pipeline")
    payload_types:       list[PayloadType]      | None = None
    mutation_strategies: list[MutationStrategy]        = Field(
        default_factory=lambda: [MutationStrategy.NONE]
    )
    request_timeout:     float = Field(default=15.0, ge=1.0, le=120.0)
    auth_headers:        dict[str, str]                = Field(default_factory=dict)
    topology:            dict[str, Any]         | None = None
    check_persistence:   bool = True
    max_payloads:        int  = Field(default=0, ge=0)


# ── Response schemas ──────────────────────────────────────────────────────────

class RunResponse(BaseModel):
    id:                   str
    target_url:           str
    framework:            str | None
    status:               RunStatus
    config:               dict[str, Any]
    total_events:         int
    findings_count:       int
    blast_radius_score:   float | None
    blast_radius_detail:  dict[str, Any] | None
    persistence_detected: bool
    persistence_detail:   dict[str, Any] | None
    error_message:        str | None
    created_at:           datetime
    started_at:           datetime | None
    completed_at:         datetime | None

    model_config = {"from_attributes": True}


class EventResponse(BaseModel):
    id:                 str
    run_id:             str
    sequence:           int
    event_type:         str
    node_id:            str | None
    payload_sent:       str | None
    response_received:  str | None
    classification:     str
    severity:           str
    duration_ms:        int | None
    # ORM attribute is event_metadata; JSON key stays "metadata" for API compat
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="event_metadata")
    timestamp:          datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class NodeDetail(BaseModel):
    id:          str
    label:       str
    type:        str
    criticality: float
    depth:       int


class BlastRadiusResponse(BaseModel):
    score:          float
    affected_nodes: list[str]
    cascade_depth:  int
    entry_node:     str
    node_details:   list[NodeDetail]
    metadata:       dict[str, Any]


class PersistenceResponse(BaseModel):
    persisted:           bool
    max_deviation:       float
    avg_deviation:       float
    deviation_by_probe:  dict[str, float]
    indicators:          list[str]
    probes_run:          int


class RunListResponse(BaseModel):
    runs:  list[RunResponse]
    total: int
