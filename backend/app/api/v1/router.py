from fastapi import APIRouter

from app.api.v1.endpoints import agents, audits, auth, engine, pipelines, public, reports, users

api_router = APIRouter()

api_router.include_router(auth.router,      prefix="/auth",      tags=["auth"])
api_router.include_router(users.router,     prefix="/users",     tags=["users"])
api_router.include_router(agents.router,    prefix="/agents",    tags=["agents"])
api_router.include_router(pipelines.router, prefix="/pipelines", tags=["pipelines"])
api_router.include_router(audits.router,    prefix="/audits",    tags=["audits"])
api_router.include_router(reports.router,   prefix="/reports",   tags=["reports"])
api_router.include_router(engine.router,    prefix="/engine",    tags=["engine"])
api_router.include_router(public.router,    prefix="/public",    tags=["public"])
