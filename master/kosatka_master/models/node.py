from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    address: Mapped[str] = mapped_column(String(255))
    api_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_type: Mapped[str] = mapped_column(String(50))  # e.g., 'agent'
    status: Mapped[str] = mapped_column(String(50), default="offline")
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role: Mapped[str] = mapped_column(String(50), default="standalone")
    upstream_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id"), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    stats: Mapped[list["NodeStat"]] = relationship(
        back_populates="node", cascade="all, delete-orphan"
    )


class NodeStat(Base):
    __tablename__ = "node_stats"

    id: Mapped[int] = mapped_column(primary_key=True)
    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id"))
    cpu_ema: Mapped[float] = mapped_column(Float)
    memory_usage: Mapped[float | None] = mapped_column(Float, nullable=True)
    disk_usage: Mapped[float | None] = mapped_column(Float, nullable=True)
    rx_bps: Mapped[float] = mapped_column(Float)
    tx_bps: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    node: Mapped["Node"] = relationship(back_populates="stats")
