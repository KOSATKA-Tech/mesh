import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from kosatka_master.models.node import Node, NodeStat
from kosatka_master.services.node_manager import NodeManager
from sqlalchemy import select


@pytest.mark.asyncio
async def test_sync_all_nodes_collects_metrics(db_session):
    tag = uuid.uuid4().hex[:8]
    node = Node(
        name=f"metrics-{tag}",
        address="http://10.0.0.1:8000",
        provider_type="agent",
        is_active=True,
        api_key="key",
    )
    db_session.add(node)
    await db_session.commit()

    fake_response = {
        "status": "ok",
        "provider": "agent",
        "metrics": {"cpu_usage_percent": 45.5, "rx_bps": 1000, "tx_bps": 2000},    }
    async def fake_sync_node(self, address):
        return fake_response

    manager = NodeManager(db_session)
    with patch(
        "kosatka_master.services.providers.agent_provider.AgentNodeProvider.sync_node",
        new=fake_sync_node,
    ):
        await manager.sync_all_nodes()

    # Verify NodeStat created
    result = await db_session.execute(select(NodeStat).where(NodeStat.node_id == node.id))
    stat = result.scalar_one()
    assert stat.cpu_ema == 45.5
    assert stat.rx_bps == 1000
    assert stat.tx_bps == 2000


@pytest.mark.asyncio
async def test_sync_all_nodes_prunes_old_stats(db_session):
    tag = uuid.uuid4().hex[:8]
    node = Node(
        name=f"prune-{tag}",
        address="http://10.0.0.2:8000",
        provider_type="agent",
        is_active=True,
        api_key="key",
    )
    db_session.add(node)
    await db_session.commit()

    # Match the timezone-aware-then-naive logic in NodeManager
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Add 25 existing stats with distinct timestamps older than 'now'
    for i in range(25):
        stat = NodeStat(
            node_id=node.id,
            cpu_ema=float(i),
            rx_bps=0.0,
            tx_bps=0.0,
            timestamp=now - timedelta(minutes=60 - i),
        )
        db_session.add(stat)
    await db_session.commit()

    fake_response = {
        "status": "ok",
        "provider": "agent",
        "metrics": {"cpu_usage_percent": 99.9, "rx_bps": 0, "tx_bps": 0},    }
    async def fake_sync_node(self, address):
        return fake_response

    manager = NodeManager(db_session)
    with patch(
        "kosatka_master.services.providers.agent_provider.AgentNodeProvider.sync_node",
        new=fake_sync_node,
    ):
        await manager.sync_all_nodes()

    # Should only have 20 stats left
    result = await db_session.execute(
        select(NodeStat).where(NodeStat.node_id == node.id).order_by(NodeStat.timestamp.desc())
    )
    stats = result.scalars().all()
    print(f"Stats count: {len(stats)}")
    for s in stats:
        print(f"Stat: ts={s.timestamp}, cpu={s.cpu_ema}")

    assert len(stats) == 20
    assert stats[0].cpu_ema == 99.9
