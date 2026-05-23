from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models.audit import Audit
from app.models.execution import ExecutionRun, RunStatus
from app.models.pipeline import Pipeline

router = APIRouter()


class ReportListItem(BaseModel):
    id: str
    audit_name: str | None
    pipeline_name: str
    findings_count: int
    blast_radius_score: float | None
    persistence_detected: bool
    completed_at: datetime | None
    generated_at: datetime


def _make_item(run: ExecutionRun, audit_name: str | None, pipeline_name: str | None) -> ReportListItem:
    generated = run.completed_at or run.created_at
    return ReportListItem(
        id=run.id,
        audit_name=audit_name,
        pipeline_name=pipeline_name or "Unknown",
        findings_count=run.findings_count,
        blast_radius_score=run.blast_radius_score,
        persistence_detected=run.persistence_detected,
        completed_at=run.completed_at,
        generated_at=generated,
    )


@router.get("/", response_model=list[ReportListItem], dependencies=[Depends(get_current_user)])
async def list_reports(db: AsyncSession = Depends(get_db)) -> list[ReportListItem]:
    result = await db.execute(
        select(ExecutionRun, Audit.name.label("audit_name"), Pipeline.name.label("pipeline_name"))
        .outerjoin(Audit,     ExecutionRun.audit_id     == Audit.id)
        .outerjoin(Pipeline,  ExecutionRun.pipeline_id  == Pipeline.id)
        .where(ExecutionRun.status == RunStatus.completed)
        .order_by(ExecutionRun.completed_at.desc())
    )
    return [_make_item(run, audit_name, pipeline_name) for run, audit_name, pipeline_name in result.all()]


@router.get("/{report_id}", dependencies=[Depends(get_current_user)])
async def get_report(report_id: str, db: AsyncSession = Depends(get_db)) -> ReportListItem:
    result = await db.execute(
        select(ExecutionRun, Audit.name.label("audit_name"), Pipeline.name.label("pipeline_name"))
        .outerjoin(Audit,     ExecutionRun.audit_id     == Audit.id)
        .outerjoin(Pipeline,  ExecutionRun.pipeline_id  == Pipeline.id)
        .where(ExecutionRun.id == report_id)
        .where(ExecutionRun.status == RunStatus.completed)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    run, audit_name, pipeline_name = row
    return _make_item(run, audit_name, pipeline_name)
