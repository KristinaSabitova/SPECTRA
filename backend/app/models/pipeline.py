import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, DateTime, func, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Pipeline(Base):
    __tablename__ = "pipelines"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))
    endpoint_url: Mapped[str | None] = mapped_column(String(500))
    framework: Mapped[str | None] = mapped_column(String(50))
    definition: Mapped[dict | None] = mapped_column(JSON)
    # NULL = legacy global pipeline (admin-only visibility); set to creator's user id otherwise
    owner_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
