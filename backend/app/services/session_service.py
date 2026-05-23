from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import generate_refresh_token
from app.models.session import Session


class SessionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: str, ip: str, user_agent: str | None) -> tuple[Session, str]:
        raw_token, token_hash = generate_refresh_token()
        session = Session(
            user_id=user_id,
            refresh_token_hash=token_hash,
            ip_address=ip,
            user_agent=user_agent,
            expires_at=datetime.now(timezone.utc) + settings.refresh_token_expire,
        )
        self.db.add(session)
        await self.db.flush()
        return session, raw_token

    async def get_by_id(self, session_id: str) -> Session | None:
        result = await self.db.execute(select(Session).where(Session.id == session_id))
        return result.scalar_one_or_none()

    async def get_by_token_hash(self, token_hash: str) -> Session | None:
        result = await self.db.execute(
            select(Session).where(
                Session.refresh_token_hash == token_hash,
                Session.revoked_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def revoke(self, session_id: str) -> bool:
        session = await self.get_by_id(session_id)
        if not session:
            return False
        session.revoked_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True

    async def revoke_all(self, user_id: str) -> int:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            update(Session)
            .where(Session.user_id == user_id, Session.revoked_at.is_(None))
            .values(revoked_at=now)
            .execution_options(synchronize_session=False)
        )
        return result.rowcount  # type: ignore[return-value]

    async def list_active(self, user_id: str) -> list[Session]:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(Session)
            .where(
                Session.user_id == user_id,
                Session.revoked_at.is_(None),
                Session.expires_at > now,
            )
            .order_by(Session.created_at.desc())
        )
        return list(result.scalars().all())
