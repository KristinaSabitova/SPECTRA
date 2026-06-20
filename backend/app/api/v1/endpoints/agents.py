from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/")
async def list_agents():
    return []


@router.post("/")
async def create_agent():
    return {}


@router.get("/{agent_id}")
async def get_agent(agent_id: str):
    return {"id": agent_id}
