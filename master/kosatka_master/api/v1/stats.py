from fastapi import APIRouter, Depends
from kosatka_master.database import get_db
from kosatka_master.models.client import Client
from kosatka_master.models.node import Node
from kosatka_master.models.subscription import Subscription
from kosatka_master.security import get_api_key
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/stats", tags=["stats"], dependencies=[Depends(get_api_key)])


@router.get("/summary/")
async def get_stats(db: AsyncSession = Depends(get_db)):
    nodes_count = await db.scalar(select(func.count(Node.id)))
    clients_count = await db.scalar(select(func.count(Client.id)))
    active_subs_count = await db.scalar(
        select(func.count(Subscription.id)).where(Subscription.is_active.is_(True))
    )

    return {
        "total_nodes": nodes_count,
        "total_clients": clients_count,
        "active_subscriptions": active_subs_count,
    }


@router.get("/realtime")
async def get_realtime_stats(db: AsyncSession = Depends(get_db)):
    stmt = select(Node).where(Node.is_active.is_(True)).options(selectinload(Node.stats))
    result = await db.execute(stmt)
    nodes = result.scalars().all()

    nodes_stats = []
    for node in nodes:
        # Get 5 most recent stats
        recent_stats = sorted(node.stats, key=lambda s: s.timestamp, reverse=True)[:5]
        nodes_stats.append(
            {
                "id": node.id,
                "name": node.name,
                "cpu_history": [s.cpu_ema for s in reversed(recent_stats)],
                "rx_history": [s.rx_bps for s in reversed(recent_stats)],
                "tx_history": [s.tx_bps for s in reversed(recent_stats)],
                "status": node.status,
            }
        )

    return {"nodes": nodes_stats}
