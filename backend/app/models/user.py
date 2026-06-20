import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class UserRole(str, Enum):
    admin = "admin"
    senior = "senior"
    junior = "junior"
    trial = "trial"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=UserRole.junior)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    is_temporary_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # TOTP 2FA
    totp_secret_enc: Mapped[str | None] = mapped_column(String(512))  # cifrado con Fernet
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    backup_codes_hash: Mapped[list | None] = mapped_column(JSON)  # lista de hashes SHA-256
    # Pending enrollment — cleared once confirmed or after TTL
    totp_pending_secret_enc: Mapped[str | None] = mapped_column(String(512))
    totp_pending_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
