import logging
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from typing import Annotated

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_client_ip, get_current_user, require_roles
from app.core.rate_limiter import auth_limiter
from jwt.exceptions import InvalidTokenError

from app.core.security import decode_token
from app.db.database import get_db
from app.models.pipeline import Pipeline
from app.models.user import User, UserRole
from app.schemas.auth import (
    AuditLogEntry,
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    RegisterPrivilegedRequest,
    RegisterRequest,
    SessionResponse,
    TOTPDisableRequest,
    TOTPLoginRequest,
    TOTPSetupResponse,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import AuthService
from app.services.session_service import SessionService
from app.config import settings

router = APIRouter()
_log = logging.getLogger("spectra.auth")

# ── Demo pipeline seed ────────────────────────────────────────────────────────
# Change these via DEMO_RAILWAY_URL / DEMO_LAB_URL env vars (set in .env).
_DEMO_RAILWAY_URL: str = settings.demo_railway_url
_DEMO_LAB_URL: str = settings.demo_lab_url

_DEMO_PIPELINES = [
    {
        "name": "Demo — Agente resistente (Railway)",
        "description": "Agente de referencia que resiste inyección indirecta. Úsalo como baseline.",
        "endpoint_url": _DEMO_RAILWAY_URL or None,
        "framework": "langchain",
    },
    {
        "name": "Demo — Lab Agent (vulnerable)",
        "description": "Agente de laboratorio para demostrar hallazgos de indirect prompt injection.",
        "endpoint_url": _DEMO_LAB_URL or None,
        "framework": "langchain",
    },
]


async def _seed_demo_pipelines(db: AsyncSession, user_id: str) -> None:
    try:
        existing = await db.execute(
            select(Pipeline).where(Pipeline.owner_id == user_id).limit(1)
        )
        if existing.scalar_one_or_none():
            return
        seeded = 0
        for spec in _DEMO_PIPELINES:
            if not spec["endpoint_url"]:
                _log.warning("Skipping demo pipeline %r: endpoint_url not configured", spec["name"])
                continue
            db.add(Pipeline(id=str(uuid.uuid4()), owner_id=user_id, **spec))
            seeded += 1
        if seeded:
            await db.commit()
    except Exception:
        _log.exception("Failed to seed demo pipelines for user %s", user_id)


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=settings.jwt_refresh_token_expire_days * 86400,
        path="/api/v1/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key="refresh_token", path="/api/v1/auth", httponly=True, secure=True, samesite="strict")


_BACKUP_CODE_RE = re.compile(r'^[0-9A-F]{4}-[0-9A-F]{4}$')


class TOTPEnableConfirmRequest(BaseModel):
    code: str
    backup_codes: Annotated[
        list[Annotated[str, Field(max_length=12)]],
        Field(min_length=8, max_length=10)
    ]

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 6:
            raise ValueError("code must be 6 digits")
        return v

    @field_validator("backup_codes")
    @classmethod
    def validate_backup_codes(cls, v: list[str]) -> list[str]:
        for code in v:
            if not _BACKUP_CODE_RE.match(code):
                raise ValueError("Invalid backup code format")
        return v


def _svc(db: AsyncSession) -> AuthService:
    return AuthService(db)


def _current_session_id(request: Request) -> str:
    try:
        token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        payload = decode_token(token)
        return payload["sid"]
    except (InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")


# ─────────────────────────── setup ──────────────────────────────────────────

@router.get("/setup-status")
async def setup_status(db: AsyncSession = Depends(get_db)):
    needs_setup = await _svc(db).get_setup_status()
    return {"needs_setup": needs_setup}


@router.post("/setup/admin", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def setup_admin(
    body: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await auth_limiter.check(f"setup:{get_client_ip(request)}")
    user = await _svc(db).setup_admin(body.email, body.username, body.password)
    return UserResponse.model_validate(user)


# ─────────────────────────── registro ───────────────────────────────────────

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    ip = get_client_ip(request)
    # Rate limit: 5 registration attempts per IP per minute
    await auth_limiter.check(f"register:{ip}")
    code_map = settings.invite_code_map
    if code_map:
        granted_role_str = code_map.get(body.invite_code)
        if granted_role_str is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Código de invitación inválido")
        try:
            role = UserRole(granted_role_str)
        except ValueError:
            _log.error("INVITE_CODES config contains unknown role %r", granted_role_str)
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Server configuration error")
    else:
        role = UserRole.junior

    user = await _svc(db).register(
        email=body.email,
        username=body.username,
        password=body.password,
        role=role,
    )
    await _seed_demo_pipelines(db, user.id)
    return UserResponse.model_validate(user)


@router.post(
    "/register/privileged",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_privileged(
    body: RegisterPrivilegedRequest,
    db: AsyncSession = Depends(get_db),
    requester: User = Depends(require_roles(UserRole.admin)),
):
    user = await _svc(db).register(
        email=body.email,
        username=body.username,
        password=body.password,
        role=body.role,
        requester=requester,
    )
    return UserResponse.model_validate(user)


# ─────────────────────────── login ──────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    ip = get_client_ip(request)
    # Rate limit: 5 login attempts per IP per minute
    await auth_limiter.check(f"login:{ip}")
    ua = request.headers.get("User-Agent")
    result = await _svc(db).login(body.email, body.password, ip, ua)
    # Reset rate limit on successful credential check (2FA may still be required)
    if not result.get("requires_2fa"):
        auth_limiter.reset(f"login:{ip}")
    if result.get("tokens"):
        _set_refresh_cookie(response, result["tokens"]["refresh_token"])
    return LoginResponse(**result)


@router.post("/login/2fa", response_model=LoginResponse)
async def login_2fa(
    body: TOTPLoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    ip = get_client_ip(request)
    # Rate limit: 5 2FA attempts per IP per minute (separate key)
    await auth_limiter.check(f"2fa:{ip}")
    ua = request.headers.get("User-Agent")
    result = await _svc(db).complete_2fa(body.temp_token, body.code, ip, ua)
    auth_limiter.reset(f"2fa:{ip}")
    if result.get("tokens"):
        _set_refresh_cookie(response, result["tokens"]["refresh_token"])
    return LoginResponse(requires_2fa=False, **result)


# ─────────────────────────── tokens ─────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing refresh token")
    ip = get_client_ip(request)
    await auth_limiter.check(f"refresh:{ip}")
    ua = request.headers.get("User-Agent")
    tokens = await _svc(db).refresh_tokens(refresh_token, ip, ua)
    _set_refresh_cookie(response, tokens["refresh_token"])
    return TokenResponse(**tokens)


# ─────────────────────────── logout ─────────────────────────────────────────

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session_id = _current_session_id(request)
    ip = get_client_ip(request)
    ua = request.headers.get("User-Agent")
    await _svc(db).logout(session_id, current_user.id, ip, ua)
    _clear_refresh_cookie(response)


@router.post("/logout/all")
async def logout_all(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ip = get_client_ip(request)
    ua = request.headers.get("User-Agent")
    count = await _svc(db).logout_all(current_user.id, ip, ua)
    _clear_refresh_cookie(response)
    return {"sessions_revoked": count}


# ─────────────────────────── perfil y contraseña ─────────────────────────────

@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ip = get_client_ip(request)
    await auth_limiter.check(f"passwd:{ip}")
    ua = request.headers.get("User-Agent")
    await _svc(db).change_password(current_user, body.current_password, body.new_password, ip, ua)


# ─────────────────────────── sesiones ────────────────────────────────────────

@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_sid = _current_session_id(request)
    sessions = await SessionService(db).list_active(current_user.id)
    return [
        SessionResponse(
            id=s.id,
            ip_address=s.ip_address,
            user_agent=s.user_agent,
            created_at=s.created_at,
            expires_at=s.expires_at,
            is_current=(s.id == current_sid),
        )
        for s in sessions
    ]


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = SessionService(db)
    session = await svc.get_by_id(session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    await svc.revoke(session_id)
    await db.commit()


# ─────────────────────────── 2FA ─────────────────────────────────────────────

@router.post("/2fa/setup", response_model=TOTPSetupResponse)
async def setup_2fa(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _svc(db).setup_totp(current_user)


@router.post("/2fa/enable")
async def enable_2fa(
    body: TOTPEnableConfirmRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ip = get_client_ip(request)
    ua = request.headers.get("User-Agent")
    await _svc(db).enable_totp(
        current_user, body.code, body.backup_codes, ip, ua
    )
    return {"enabled": True}


@router.delete("/2fa")
async def disable_2fa(
    body: TOTPDisableRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ip = get_client_ip(request)
    await auth_limiter.check(f"2fa-disable:{ip}")
    ua = request.headers.get("User-Agent")
    await _svc(db).disable_totp(current_user, body.code, ip, ua)
    return {"disabled": True}


# ─────────────────────────── audit log ───────────────────────────────────────

@router.get("/audit-log", response_model=list[AuditLogEntry])
async def get_audit_log(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the personal audit log for the authenticated user."""
    entries = await _svc(db).get_audit_log(current_user.id, limit=limit, offset=offset)
    return [AuditLogEntry.model_validate(e) for e in entries]
