from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_roles
from app.db.database import get_db
from app.models.audit import Audit
from app.models.pipeline import Pipeline
from app.models.user import UserRole

router = APIRouter()


class CreatePipelineRequest(BaseModel):
    name: str
    endpoint_url: str
    framework: str
    description: str | None = None


class PipelineResponse(BaseModel):
    id: str
    name: str
    description: str | None
    endpoint_url: str | None
    framework: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[PipelineResponse], dependencies=[Depends(get_current_user)])
async def list_pipelines(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Pipeline).order_by(Pipeline.created_at.desc()))
    return result.scalars().all()


@router.post("/", response_model=PipelineResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_roles(UserRole.admin, UserRole.senior))])
async def create_pipeline(body: CreatePipelineRequest, db: AsyncSession = Depends(get_db)):
    pipeline = Pipeline(
        id=str(uuid.uuid4()),
        name=body.name.strip(),
        description=body.description,
        endpoint_url=body.endpoint_url.strip(),
        framework=body.framework,
    )
    db.add(pipeline)
    await db.commit()
    await db.refresh(pipeline)
    return pipeline


@router.get("/{pipeline_id}", response_model=PipelineResponse, dependencies=[Depends(get_current_user)])
async def get_pipeline(pipeline_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline not found")
    return pipeline


@router.delete("/{pipeline_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_roles(UserRole.admin, UserRole.senior))])
async def delete_pipeline(pipeline_id: str, db: AsyncSession = Depends(get_db)) -> Response:
    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline not found")

    audit_count = (await db.execute(
        select(Audit).where(Audit.pipeline_id == pipeline_id).limit(1)
    )).scalar_one_or_none()
    if audit_count is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pipeline has associated audits. Delete them first.",
        )

    await db.delete(pipeline)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
