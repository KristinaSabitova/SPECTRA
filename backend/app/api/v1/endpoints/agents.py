from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_agents():
    return []


@router.post("/")
async def create_agent():
    return {}


@router.get("/{agent_id}")
async def get_agent(agent_id: str):
    return {"id": agent_id}
