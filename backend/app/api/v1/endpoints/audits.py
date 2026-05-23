from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models.audit import Audit, AuditStatus
from app.models.pipeline import Pipeline

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


@router.get("/", response_model=list[AuditResponse], dependencies=[Depends(get_current_user)])
async def list_audits(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Audit, Pipeline.name.label("pipeline_name"))
        .outerjoin(Pipeline, Audit.pipeline_id == Pipeline.id)
        .order_by(Audit.created_at.desc())
    )
    return [_row_to_response(audit, pipeline_name or "Unknown") for audit, pipeline_name in result.all()]


@router.post("/", response_model=AuditResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(get_current_user)])
async def create_audit(body: CreateAuditRequest, db: AsyncSession = Depends(get_db)):
    pipeline_result = await db.execute(select(Pipeline).where(Pipeline.id == body.pipeline_id))
    pipeline = pipeline_result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline not found")

    audit = Audit(
        id=str(uuid.uuid4()),
        pipeline_id=body.pipeline_id,
        name=body.name,
        status=AuditStatus.pending,
    )
    db.add(audit)
    await db.commit()
    await db.refresh(audit)
    return _row_to_response(audit, pipeline.name)


@router.get("/{audit_id}", response_model=AuditResponse, dependencies=[Depends(get_current_user)])
async def get_audit(audit_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Audit, Pipeline.name.label("pipeline_name"))
        .outerjoin(Pipeline, Audit.pipeline_id == Pipeline.id)
        .where(Audit.id == audit_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found")
    audit, pipeline_name = row
    return _row_to_response(audit, pipeline_name or "Unknown")


@router.delete("/{audit_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(get_current_user)])
async def delete_audit(audit_id: str, db: AsyncSession = Depends(get_db)) -> Response:
    result = await db.execute(select(Audit).where(Audit.id == audit_id))
    audit = result.scalar_one_or_none()
    if not audit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found")
    await db.delete(audit)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
