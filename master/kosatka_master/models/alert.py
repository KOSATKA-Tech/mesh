from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class SystemAlert(Base):
    __tablename__ = "system_alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    level: Mapped[str] = mapped_column(String(50), default="info")  # info, warning, error, critical
    source: Mapped[str] = mapped_column(String(255))  # Node name or "Master"
    message: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class AdminUser(Base):
    """Super-admins with web dashboard access."""

    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class SystemConfig(Base):
    """Dynamic application settings stored in DB."""

    __tablename__ = "system_config"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[str] = mapped_column(Text)  # JSON serialized or raw string
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
