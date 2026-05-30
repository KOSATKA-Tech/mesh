import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(255), unique=True)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sub_token: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, default=lambda: str(uuid.uuid4())
    )
    sub_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # Node on which the agent actually materialised this client's peer.
    # Recorded at provision time so the master can route config/revoke
    # requests back to the right agent without relying on the caller
    # passing node_id. Nullable for rows created before this column existed
    # (SQLite ADD COLUMN can't backfill, so we treat NULL as "unknown —
    # fall back to active-node scan").
    node_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("nodes.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    is_trial: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
