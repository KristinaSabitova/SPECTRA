from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401 — must be imported before create_all to register all tables
from app.api.v1.router import api_router
from app.config import settings, validate_secrets
from app.db.database import Base, engine


@asynccontextmanager
async def lifespan(_app: FastAPI):
    validate_secrets()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="SPECTRA",
    description="Red team auditing platform for AI agent pipelines",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Origins are read from ALLOWED_ORIGINS env variable (see config.py).
# Never use ["*"] in production: it disables credentials and exposes the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Security headers ──────────────────────────────────────────────────────────
# Applied to every response so browsers can enforce security policies even if
# a frontend CDN or proxy forgets to add them.
@app.middleware("http")
async def security_headers(request: Request, call_next) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = (
        "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
        "magnetometer=(), microphone=(), payment=(), usb=()"
    )
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )
    # HSTS only makes sense over HTTPS (nginx handles TLS in production)
    if request.url.scheme == "https" or settings.app_env == "production":
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains; preload"
        )
    return response


app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "spectra-backend"}
