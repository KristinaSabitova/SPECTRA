"""
Engine API endpoints.

Provides:
  POST /engine/runs            – create + start a new audit run
  GET  /engine/runs            – list runs (own runs; admin sees all)
  GET  /engine/runs/{id}       – get run details
  GET  /engine/runs/{id}/events – list persisted events for a run
  GET  /engine/runs/{id}/events/stream – SSE real-time event stream
  POST /engine/runs/{id}/cancel – cancel a queued/running run
  GET  /engine/runs/{id}/report – download run report (markdown|pdf|html)
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import get_current_user, require_roles
from app.core.ssrf_protection import validate_target_url
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
_log = logging.getLogger("spectra.engine")


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_run_or_404(run_id: str, db: AsyncSession) -> ExecutionRun:
    result = await db.execute(select(ExecutionRun).where(ExecutionRun.id == run_id))
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run


def _assert_owner(run: ExecutionRun, user: User) -> None:
    """Raise 403 if the run does not belong to the user (admins bypass the check)."""
    if UserRole(user.role) == UserRole.admin:
        return
    if run.user_id is None or run.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this run.",
        )


async def _check_daily_limit(user_id: str, db: AsyncSession) -> None:
    """Enforce MAX_RUNS_PER_DAY limit per user."""
    if settings.max_runs_per_day <= 0:
        return
    start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    count_result = await db.execute(
        select(func.count()).where(
            ExecutionRun.user_id == user_id,
            ExecutionRun.created_at >= start_of_day,
        )
    )
    count = count_result.scalar_one()
    if count >= settings.max_runs_per_day:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily run limit ({settings.max_runs_per_day}) reached.",
        )


# ── Create + start run ────────────────────────────────────────────────────────

@router.post(
    "/runs",
    response_model=RunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_roles(UserRole.admin, UserRole.senior))],
)
async def create_run(
    body: CreateRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RunResponse:
    # SSRF: validate the target URL resolves to a public address
    validate_target_url(body.target_url)

    # Enforce per-user daily limit
    await _check_daily_limit(current_user.id, db)

    # Clamp request_timeout to server-side maximum
    timeout = min(body.request_timeout, float(settings.max_run_timeout_seconds))

    expires_at = (
        datetime.now(timezone.utc) + timedelta(days=settings.data_retention_days)
        if settings.data_retention_days > 0
        else None
    )

    run_id = str(uuid.uuid4())
    run = ExecutionRun(
        id=run_id,
        user_id=current_user.id,
        target_url=body.target_url,
        status=RunStatus.queued,
        expires_at=expires_at,
        config={
            "payload_types": [t.value for t in body.payload_types] if body.payload_types else None,
            "mutation_strategies": [m.value for m in body.mutation_strategies],
            "request_timeout": timeout,
            "check_persistence": body.check_persistence,
            "max_payloads": body.max_payloads,
        },
        created_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.flush()
    await db.commit()

    _log.info(
        "run_created user_id=%s run_id=%s target=%s",
        current_user.id,
        run_id,
        body.target_url,
    )

    asyncio.create_task(
        _run_task(run_id, body, timeout),
        name=f"spectra-run-{run_id}",
    )

    result = await db.execute(select(ExecutionRun).where(ExecutionRun.id == run_id))
    run = result.scalar_one()
    return RunResponse.model_validate(run)


async def _run_task(run_id: str, body: CreateRunRequest, timeout: float) -> None:
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
                request_timeout=timeout,
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
)
async def list_runs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RunListResponse:
    # Admins see all runs; regular users see only their own
    is_admin = UserRole(current_user.role) == UserRole.admin
    base_filter = [] if is_admin else [ExecutionRun.user_id == current_user.id]

    result = await db.execute(
        select(ExecutionRun)
        .where(*base_filter)
        .order_by(ExecutionRun.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    runs = result.scalars().all()

    count_result = await db.execute(
        select(func.count()).where(*base_filter)
    )
    total = count_result.scalar_one()

    return RunListResponse(
        runs=[RunResponse.model_validate(r) for r in runs],
        total=total,
    )


# ── Get run ───────────────────────────────────────────────────────────────────

@router.get(
    "/runs/{run_id}",
    response_model=RunResponse,
)
async def get_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RunResponse:
    run = await _get_run_or_404(run_id, db)
    _assert_owner(run, current_user)
    return RunResponse.model_validate(run)


# ── List events ───────────────────────────────────────────────────────────────

@router.get(
    "/runs/{run_id}/events",
    response_model=list[EventResponse],
)
async def list_events(
    run_id: str,
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[EventResponse]:
    run = await _get_run_or_404(run_id, db)
    _assert_owner(run, current_user)

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
)
async def stream_events(
    run_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    run = await _get_run_or_404(run_id, db)
    _assert_owner(run, current_user)

    if run.status in (RunStatus.completed, RunStatus.failed, RunStatus.cancelled):
        return StreamingResponse(
            _replay_from_db(run_id, db),
            media_type="text/event-stream",
        )

    return StreamingResponse(
        _live_stream(run_id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _replay_from_db(run_id: str, db: AsyncSession):
    result = await db.execute(
        select(ExecutionEvent)
        .where(ExecutionEvent.run_id == run_id)
        .order_by(ExecutionEvent.sequence)
    )
    for event in result.scalars():
        data = json.dumps({
            "id": event.id,
            "run_id": event.run_id,
            "sequence": event.sequence,
            "event_type": event.event_type,
            "node_id": event.node_id,
            "severity": event.severity,
            "classification": event.classification,
            "duration_ms": event.duration_ms,
            "metadata": event.event_metadata,
            "timestamp": event.timestamp.isoformat(),
        })
        yield f"event: engine\ndata: {data}\n\n"
    yield "event: done\ndata: {}\n\n"


async def _live_stream(run_id: str, request: Request):
    queue: asyncio.Queue = event_bus.subscribe(run_id)
    try:
        while True:
            if await request.is_disconnected():
                break
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
                continue

            if event_bus.is_sentinel(event):
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RunResponse:
    run = await _get_run_or_404(run_id, db)
    _assert_owner(run, current_user)

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


# ── Report download ───────────────────────────────────────────────────────────

@router.get("/runs/{run_id}/report")
async def get_run_report(
    run_id: str,
    format: Literal["markdown", "pdf", "html"] = "markdown",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    run = await _get_run_or_404(run_id, db)
    _assert_owner(run, current_user)

    events_result = await db.execute(
        select(ExecutionEvent)
        .where(ExecutionEvent.run_id == run_id)
        .order_by(ExecutionEvent.sequence)
    )
    events = events_result.scalars().all()

    from app.services.report_generator import RunReportGenerator
    gen = RunReportGenerator(run=run, events=list(events))

    safe_id = run_id[:8]
    if format == "pdf":
        content, mime = gen.to_pdf(), "application/pdf"
        filename = f"spectra-report-{safe_id}.pdf"
    elif format == "html":
        content, mime = gen.to_html().encode(), "text/html; charset=utf-8"
        filename = f"spectra-report-{safe_id}.html"
    else:
        content, mime = gen.to_markdown().encode(), "text/markdown; charset=utf-8"
        filename = f"spectra-report-{safe_id}.md"

    return Response(
        content=content,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
