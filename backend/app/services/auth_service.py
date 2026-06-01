import secrets
import string

from fastapi import HTTPException, status
from jose import JWTError
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_2fa_temp_token,
    create_access_token,
    decode_token,
    hash_refresh_token,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.models.access_log import AccessLog
from app.models.session import Session
from app.models.user import User, UserRole
from app.services.session_service import SessionService
from app.services.totp_service import TOTPService


def _gen_temp_password() -> str:
    chars = list(
        secrets.choice(string.ascii_uppercase)
        + secrets.choice(string.ascii_lowercase)
        + secrets.choice(string.digits)
        + secrets.choice('!@#$%^&*')
        + ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
    )
    secrets.SystemRandom().shuffle(chars)
    return ''.join(chars)


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._session_svc = SessionService(db)
        self._totp_svc = TOTPService()

    # ------------------------------------------------------------------ helpers

    async def _log(
        self,
        action: str,
        success: bool,
        ip: str,
        user_agent: str | None,
        user_id: str | None = None,
        email: str | None = None,
        detail: dict | None = None,
    ) -> None:
        # Never log passwords, tokens, or agent responses
        self.db.add(
            AccessLog(
                user_id=user_id,
                email_attempted=email,
                ip_address=ip,
                user_agent=user_agent,
                action=action,
                success=success,
                detail=detail,
            )
        )

    async def _get_user_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def _get_user_by_id(self, user_id: str) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    def _build_tokens(self, user: User, session: Session, raw_refresh: str) -> dict:
        from app.config import settings

        access_token = create_access_token(user.id, user.role, session.id)
        return {
            "access_token": access_token,
            "refresh_token": raw_refresh,
            "token_type": "bearer",
            "expires_in": int(settings.access_token_expire.total_seconds()),
        }

    # ------------------------------------------------------------------ setup

    async def get_setup_status(self) -> bool:
        result = await self.db.execute(select(User).limit(1))
        return result.scalar_one_or_none() is None

    async def setup_admin(self, email: str, username: str, password: str) -> User:
        if not await self.get_setup_status():
            raise HTTPException(status.HTTP_409_CONFLICT, "Setup already completed")

        dup = await self.db.execute(
            select(User).where(or_(User.email == email, User.username == username))
        )
        if dup.scalar_one_or_none():
            raise HTTPException(status.HTTP_409_CONFLICT, "Email or username already taken")

        user = User(
            email=email,
            username=username,
            password_hash=hash_password(password),
            role=UserRole.admin,
            is_temporary_password=False,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        await self._log("setup_admin", True, "internal", None, user_id=user.id)
        await self.db.commit()
        return user

    # ------------------------------------------------------------------ auth ops

    async def register(
        self,
        email: str,
        username: str,
        password: str,
        role: UserRole,
        requester: User | None = None,
    ) -> User:
        if role in (UserRole.admin, UserRole.senior):
            if not requester or requester.role != UserRole.admin:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    "Only admins can assign admin or senior roles",
                )

        dup = await self.db.execute(
            select(User).where(or_(User.email == email, User.username == username))
        )
        if dup.scalar_one_or_none():
            raise HTTPException(status.HTTP_409_CONFLICT, "Email or username already taken")

        user = User(
            email=email,
            username=username,
            password_hash=hash_password(password),
            role=role,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        await self._log("register", True, "internal", None, user_id=user.id)
        await self.db.commit()
        return user

    async def create_user(
        self, email: str, username: str, role: UserRole, requester: User
    ) -> tuple[User, str]:
        dup = await self.db.execute(
            select(User).where(or_(User.email == email, User.username == username))
        )
        if dup.scalar_one_or_none():
            raise HTTPException(status.HTTP_409_CONFLICT, "Email or username already taken")

        temp_pw = _gen_temp_password()
        user = User(
            email=email,
            username=username,
            password_hash=hash_password(temp_pw),
            role=role,
            is_temporary_password=True,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        await self._log(
            "create_user", True, "internal", None,
            user_id=requester.id, detail={"new_user_id": user.id}
        )
        await self.db.commit()
        return user, temp_pw

    async def login(
        self, email: str, password: str, ip: str, user_agent: str | None
    ) -> dict:
        user = await self._get_user_by_email(email.lower().strip())

        if not user or not verify_password(password, user.password_hash):
            await self._log("login", False, ip, user_agent, email=email)
            await self.db.commit()
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

        if not user.is_active:
            await self._log("login", False, ip, user_agent, user_id=user.id)
            await self.db.commit()
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")

        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)

        if user.totp_enabled:
            temp_token = create_2fa_temp_token(user.id)
            await self._log("login_2fa_required", True, ip, user_agent, user_id=user.id)
            await self.db.commit()
            return {"requires_2fa": True, "temp_token": temp_token}

        session, raw_refresh = await self._session_svc.create(user.id, ip, user_agent)
        await self._log("login", True, ip, user_agent, user_id=user.id)
        await self.db.commit()

        # Enforce 2FA setup on first login — signal the frontend to redirect
        must_setup_totp = not user.totp_enabled

        return {
            "requires_2fa": False,
            "must_change_password": user.is_temporary_password,
            "must_setup_totp": must_setup_totp,
            "tokens": self._build_tokens(user, session, raw_refresh),
            "user": user,
        }

    async def complete_2fa(
        self, temp_token: str, code: str, ip: str, user_agent: str | None
    ) -> dict:
        try:
            payload = decode_token(temp_token)
            if payload.get("type") != "2fa_pending":
                raise ValueError
            user_id: str = payload["sub"]
        except (JWTError, KeyError, ValueError):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired 2FA token")

        user = await self._get_user_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

        valid, used_backup = self._totp_svc.verify(user, code)
        if not valid:
            await self._log("2fa_verify", False, ip, user_agent, user_id=user.id)
            await self.db.commit()
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid 2FA code")

        if used_backup:
            self._totp_svc.consume_backup_code(user, code)

        session, raw_refresh = await self._session_svc.create(user.id, ip, user_agent)
        await self._log("2fa_verify", True, ip, user_agent, user_id=user.id)
        await self.db.commit()

        return {
            "tokens": self._build_tokens(user, session, raw_refresh),
            "user": user,
        }

    async def refresh_tokens(
        self, raw_refresh_token: str, ip: str, user_agent: str | None
    ) -> dict:
        token_hash = hash_refresh_token(raw_refresh_token)
        session = await self._session_svc.get_by_token_hash(token_hash)

        if not session or not session.is_active:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")

        user = await self._get_user_by_id(session.user_id)
        if not user or not user.is_active:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

        # Token rotation: invalidate the old session, create a new one
        await self._session_svc.revoke(session.id)
        new_session, new_raw = await self._session_svc.create(user.id, ip, user_agent)
        await self._log("token_refresh", True, ip, user_agent, user_id=user.id)
        await self.db.commit()

        return self._build_tokens(user, new_session, new_raw)

    async def logout(
        self, session_id: str, user_id: str, ip: str, user_agent: str | None
    ) -> None:
        await self._session_svc.revoke(session_id)
        await self._log("logout", True, ip, user_agent, user_id=user_id)
        await self.db.commit()

    async def logout_all(
        self, user_id: str, ip: str, user_agent: str | None
    ) -> int:
        count = await self._session_svc.revoke_all(user_id)
        await self._log(
            "logout_all", True, ip, user_agent,
            user_id=user_id, detail={"sessions_revoked": count}
        )
        await self.db.commit()
        return count

    async def change_password(
        self, user: User, current_password: str, new_password: str,
        ip: str, user_agent: str | None
    ) -> None:
        if not verify_password(current_password, user.password_hash):
            await self._log("password_change", False, ip, user_agent, user_id=user.id)
            await self.db.commit()
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Current password is incorrect")

        user.password_hash = hash_password(new_password)
        user.is_temporary_password = False
        await self._log("password_change", True, ip, user_agent, user_id=user.id)
        await self.db.commit()

    # ------------------------------------------------------------------ 2FA ops

    async def setup_totp(self, user: User) -> dict:
        if user.totp_enabled:
            raise HTTPException(status.HTTP_409_CONFLICT, "2FA already enabled")
        return self._totp_svc.generate_setup(user.email)

    async def enable_totp(
        self, user: User, code: str, secret: str, backup_codes: list[str],
        ip: str, user_agent: str | None
    ) -> None:
        import pyotp
        if not pyotp.TOTP(secret).verify(code, valid_window=1):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid TOTP code")

        codes_hash = self._totp_svc.hash_backup_codes(backup_codes)
        self._totp_svc.apply_setup(user, secret, codes_hash)
        await self._log("2fa_enable", True, ip, user_agent, user_id=user.id)
        await self.db.commit()

    async def disable_totp(
        self, user: User, code: str, ip: str, user_agent: str | None
    ) -> None:
        if not user.totp_enabled:
            raise HTTPException(status.HTTP_409_CONFLICT, "2FA not enabled")
        valid, _ = self._totp_svc.verify(user, code)
        if not valid:
            await self._log("2fa_disable", False, ip, user_agent, user_id=user.id)
            await self.db.commit()
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid 2FA code")
        self._totp_svc.disable(user)
        await self._log("2fa_disable", True, ip, user_agent, user_id=user.id)
        await self.db.commit()

    # ------------------------------------------------------------------ audit log

    async def get_audit_log(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> list[AccessLog]:
        result = await self.db.execute(
            select(AccessLog)
            .where(AccessLog.user_id == user_id)
            .order_by(AccessLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
