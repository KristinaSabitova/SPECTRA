"""
Engine API endpoints.

Provides:
  POST /engine/runs            – create + start a new audit run
  GET  /engine/runs            – list runs
  GET  /engine/runs/{id}       – get run details
  GET  /engine/runs/{id}/events – list persisted events for a run
  GET  /engine/runs/{id}/events/stream – SSE real-time event stream
  POST /engine/runs/{id}/cancel – cancel a queued/running run
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_roles
from app.db.database import get_db
from app.engine.events import event_bus
from app.engine.execution import ExecutionRunner, ExecutionTracer, RunConfig
from app.models.execution import ExecutionEvent, ExecutionRun, RunStatus
from app.models.user import User, UserRole
from app.schemas.engine import (
    CreateRunRequest,
    EventResponse,
    RunListResponse,
    RunResponse,
)

router = APIRouter()


# ── Create + start run ────────────────────────────────────────────────────────

@router.post(
    "/runs",
    response_model=RunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_roles(UserRole.admin, UserRole.senior))],
)
async def create_run(
    body: CreateRunRequest,
    db:   AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RunResponse:
    run_id = str(uuid.uuid4())
    run = ExecutionRun(
        id=run_id,
        target_url=body.target_url,
        status=RunStatus.queued,
        config={
            "payload_types":       [t.value for t in body.payload_types] if body.payload_types else None,
            "mutation_strategies": [m.value for m in body.mutation_strategies],
            "request_timeout":     body.request_timeout,
            "check_persistence":   body.check_persistence,
            "max_payloads":        body.max_payloads,
        },
        created_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.flush()
    await db.commit()

    # Kick off async task (fire-and-forget)
    asyncio.create_task(
        _run_task(run_id, body),
        name=f"spectra-run-{run_id}",
    )

    # Re-fetch for response serialization
    result = await db.execute(select(ExecutionRun).where(ExecutionRun.id == run_id))
    run = result.scalar_one()
    return RunResponse.model_validate(run)


async def _run_task(run_id: str, body: CreateRunRequest) -> None:
    """Background task — owns its own DB session."""
    from app.db.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        async with db.begin():
            tracer = ExecutionTracer(run_id=run_id, db=db)
            await tracer.start_run()

            cfg = RunConfig(
                target_url=body.target_url,
                payload_types=body.payload_types,
                mutation_strategies=body.mutation_strategies,
                request_timeout=body.request_timeout,
                auth_headers=body.auth_headers,
                topology=body.topology,
                check_persistence=body.check_persistence,
                max_payloads=body.max_payloads,
            )
            runner = ExecutionRunner(cfg)
            try:
                await runner.run(tracer)
            except Exception:
                pass  # tracer.fail_run already called inside runner.run


# ── List runs ─────────────────────────────────────────────────────────────────

@router.get(
    "/runs",
    response_model=RunListResponse,
    dependencies=[Depends(get_current_user)],
)
async def list_runs(
    limit:  int = 20,
    offset: int = 0,
    db:     AsyncSession = Depends(get_db),
) -> RunListResponse:
    result = await db.execute(
        select(ExecutionRun)
        .order_by(ExecutionRun.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    runs = result.scalars().all()

    count_result = await db.execute(select(ExecutionRun))
    total = len(count_result.scalars().all())

    return RunListResponse(
        runs=[RunResponse.model_validate(r) for r in runs],
        total=total,
    )


# ── Get run ───────────────────────────────────────────────────────────────────

@router.get(
    "/runs/{run_id}",
    response_model=RunResponse,
    dependencies=[Depends(get_current_user)],
)
async def get_run(
    run_id: str,
    db:     AsyncSession = Depends(get_db),
) -> RunResponse:
    run = await _get_run_or_404(run_id, db)
    return RunResponse.model_validate(run)


# ── List events ───────────────────────────────────────────────────────────────

@router.get(
    "/runs/{run_id}/events",
    response_model=list[EventResponse],
    dependencies=[Depends(get_current_user)],
)
async def list_events(
    run_id: str,
    limit:  int = 200,
    offset: int = 0,
    db:     AsyncSession = Depends(get_db),
) -> list[EventResponse]:
    await _get_run_or_404(run_id, db)
    result = await db.execute(
        select(ExecutionEvent)
        .where(ExecutionEvent.run_id == run_id)
        .order_by(ExecutionEvent.sequence)
        .limit(limit)
        .offset(offset)
    )
    events = result.scalars().all()
    return [EventResponse.model_validate(e) for e in events]


# ── SSE event stream ──────────────────────────────────────────────────────────

@router.get(
    "/runs/{run_id}/events/stream",
    dependencies=[Depends(get_current_user)],
)
async def stream_events(
    run_id:  str,
    request: Request,
    db:      AsyncSession = Depends(get_db),
) -> StreamingResponse:
    run = await _get_run_or_404(run_id, db)

    # If run is already finished, replay from DB
    if run.status in (RunStatus.completed, RunStatus.failed, RunStatus.cancelled):
        return StreamingResponse(
            _replay_from_db(run_id, db),
            media_type="text/event-stream",
        )

    return StreamingResponse(
        _live_stream(run_id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control":               "no-cache",
            "X-Accel-Buffering":           "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


async def _replay_from_db(run_id: str, db: AsyncSession):
    """Yield all persisted events for a finished run."""
    result = await db.execute(
        select(ExecutionEvent)
        .where(ExecutionEvent.run_id == run_id)
        .order_by(ExecutionEvent.sequence)
    )
    for event in result.scalars():
        data = json.dumps({
            "id":          event.id,
            "run_id":      event.run_id,
            "sequence":    event.sequence,
            "event_type":  event.event_type,
            "node_id":     event.node_id,
            "severity":    event.severity,
            "classification": event.classification,
            "duration_ms": event.duration_ms,
            "metadata":    event.event_metadata,
            "timestamp":   event.timestamp.isoformat(),
        })
        yield f"event: engine\ndata: {data}\n\n"
    yield "event: done\ndata: {}\n\n"


async def _live_stream(run_id: str, request: Request):
    """Subscribe to the EventBus and forward events as SSE."""
    queue: asyncio.Queue = event_bus.subscribe(run_id)
    try:
        while True:
            if await request.is_disconnected():
                break
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
            except asyncio.TimeoutError:
                # Keep-alive ping
                yield ": keepalive\n\n"
                continue

            if event_bus.is_sentinel(event):  # run finished
                yield "event: done\ndata: {}\n\n"
                break

            yield event.to_sse()
    finally:
        event_bus.unsubscribe(run_id, queue)


# ── Cancel run ────────────────────────────────────────────────────────────────

@router.post(
    "/runs/{run_id}/cancel",
    response_model=RunResponse,
    dependencies=[Depends(require_roles(UserRole.admin, UserRole.senior))],
)
async def cancel_run(
    run_id: str,
    db:     AsyncSession = Depends(get_db),
) -> RunResponse:
    run = await _get_run_or_404(run_id, db)
    if run.status not in (RunStatus.queued, RunStatus.running):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel run in status '{run.status}'",
        )
    await db.execute(
        update(ExecutionRun)
        .where(ExecutionRun.id == run_id)
        .values(
            status=RunStatus.cancelled,
            completed_at=datetime.now(timezone.utc),
        )
        .execution_options(synchronize_session=False)
    )
    await db.flush()
    await db.commit()
    await event_bus.close(run_id)

    result = await db.execute(select(ExecutionRun).where(ExecutionRun.id == run_id))
    run = result.scalar_one()
    return RunResponse.model_validate(run)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_run_or_404(run_id: str, db: AsyncSession) -> ExecutionRun:
    result = await db.execute(select(ExecutionRun).where(ExecutionRun.id == run_id))
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run
