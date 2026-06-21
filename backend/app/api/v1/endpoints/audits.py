from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models.audit import Audit, AuditStatus
from app.models.execution import ExecutionRun, RunStatus
from app.models.pipeline import Pipeline
from app.models.user import User, UserRole

router = APIRouter()


class CreateAuditRequest(BaseModel):
    pipeline_id: str
    name: str | None = None


class AuditResponse(BaseModel):
    id: str
    pipeline_id: str
    pipeline_name: str
    name: str | None
    status: str
    findings_count: int
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


def _row_to_response(audit: Audit, pipeline_name: str) -> AuditResponse:
    return AuditResponse(
        id=audit.id,
        pipeline_id=audit.pipeline_id,
        pipeline_name=pipeline_name,
        name=audit.name,
        status=audit.status if isinstance(audit.status, str) else audit.status.value,
        findings_count=audit.findings_count,
        started_at=audit.started_at,
        completed_at=audit.completed_at,
        created_at=audit.created_at,
    )


@router.get("/", response_model=list[AuditResponse])
async def list_audits(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = (
        select(Audit, Pipeline.name.label("pipeline_name"))
        .outerjoin(Pipeline, Audit.pipeline_id == Pipeline.id)
        .outerjoin(ExecutionRun, ExecutionRun.id == Audit.id)
        .order_by(Audit.created_at.desc())
    )
    if UserRole(current_user.role) != UserRole.admin:
        q = q.where(ExecutionRun.user_id == current_user.id)
    result = await db.execute(q)
    return [_row_to_response(audit, pipeline_name or "Unknown") for audit, pipeline_name in result.all()]


@router.post("/", response_model=AuditResponse, status_code=status.HTTP_201_CREATED)
async def create_audit(
    body: CreateAuditRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pipeline_q = select(Pipeline).where(Pipeline.id == body.pipeline_id)
    if UserRole(current_user.role) != UserRole.admin:
        pipeline_q = pipeline_q.where(Pipeline.owner_id == current_user.id)
    pipeline_result = await db.execute(pipeline_q)
    pipeline = pipeline_result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline not found")

    audit_id = str(uuid.uuid4())

    audit = Audit(
        id=audit_id,
        pipeline_id=body.pipeline_id,
        name=body.name,
        status=AuditStatus.pending,
    )
    db.add(audit)

    # ExecutionRun shares the same primary key so RunDetail can fetch by audit ID
    run = ExecutionRun(
        id=audit_id,
        audit_id=audit_id,
        pipeline_id=body.pipeline_id,
        target_url=pipeline.endpoint_url,
        user_id=current_user.id,
        status=RunStatus.queued,
        config={
            "mutation_strategies": ["none"],
            "request_timeout": 15.0,
            "check_persistence": True,
            "max_payloads": 0,
        },
    )
    db.add(run)

    await db.commit()
    await db.refresh(audit)

    asyncio.create_task(
        _run_audit_task(audit_id, pipeline.endpoint_url),
        name=f"spectra-audit-{audit_id}",
    )

    return _row_to_response(audit, pipeline.name)


async def _run_audit_task(audit_id: str, target_url: str) -> None:
    from app.db.database import AsyncSessionLocal
    from app.engine.execution import ExecutionRunner, ExecutionTracer, RunConfig

    async with AsyncSessionLocal() as db:
        async with db.begin():
            await db.execute(
                update(Audit)
                .where(Audit.id == audit_id)
                .values(status=AuditStatus.running, started_at=datetime.now(timezone.utc))
                .execution_options(synchronize_session=False)
            )
            tracer = ExecutionTracer(run_id=audit_id, db=db)
            await tracer.start_run()
            cfg = RunConfig(target_url=target_url)
            runner = ExecutionRunner(cfg)
            try:
                await runner.run(tracer)
            except Exception:
                pass  # tracer.fail_run already called inside runner.run

    # Sync audit status and findings from the completed run
    async with AsyncSessionLocal() as db:
        async with db.begin():
            run_res = await db.execute(
                select(ExecutionRun).where(ExecutionRun.id == audit_id)
            )
            run = run_res.scalar_one_or_none()
            if run:
                final_status = (
                    AuditStatus.completed if run.status == RunStatus.completed
                    else AuditStatus.failed
                )
                await db.execute(
                    update(Audit)
                    .where(Audit.id == audit_id)
                    .values(
                        status=final_status,
                        findings_count=run.findings_count,
                        started_at=run.started_at,
                        completed_at=run.completed_at,
                    )
                    .execution_options(synchronize_session=False)
                )


@router.get("/{audit_id}", response_model=AuditResponse)
async def get_audit(
    audit_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = (
        select(Audit, Pipeline.name.label("pipeline_name"))
        .outerjoin(Pipeline, Audit.pipeline_id == Pipeline.id)
        .outerjoin(ExecutionRun, ExecutionRun.id == Audit.id)
        .where(Audit.id == audit_id)
    )
    if UserRole(current_user.role) != UserRole.admin:
        q = q.where(ExecutionRun.user_id == current_user.id)
    result = await db.execute(q)
    row = result.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found")
    audit, pipeline_name = row
    return _row_to_response(audit, pipeline_name or "Unknown")


@router.delete("/{audit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audit(
    audit_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    result = await db.execute(select(Audit).where(Audit.id == audit_id))
    audit = result.scalar_one_or_none()
    if not audit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found")
    # Delete the associated execution run (same ID) before the audit to avoid FK constraint
    run_result = await db.execute(select(ExecutionRun).where(ExecutionRun.id == audit_id))
    run = run_result.scalar_one_or_none()
    if run:
        if UserRole(current_user.role) != UserRole.admin and run.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found")
        await db.delete(run)
    await db.delete(audit)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
