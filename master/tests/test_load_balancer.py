from datetime import datetime, timedelta, timezone

import pytest
from kosatka_master.api.v1.clients import _pick_node
from kosatka_master.models.client import Client
from kosatka_master.models.node import Node, NodeStat
from sqlalchemy import select


@pytest.mark.asyncio
async def test_pick_node_load_balancing(db_session):
    # Setup two nodes
    node1 = Node(name="node1", address="http://node1", provider_type="awg", is_active=True)
    node2 = Node(name="node2", address="http://node2", provider_type="awg", is_active=True)
    db_session.add_all([node1, node2])
    await db_session.commit()
    await db_session.refresh(node1)
    await db_session.refresh(node2)

    # Scenario 1: Empty nodes, should pick first one (stable pick)
    picked = await _pick_node(db_session, "awg", None)
    assert picked.id in [node1.id, node2.id]

    # Scenario 2: node1 has more clients
    c1 = Client(external_id="c1", node_id=node1.id, is_active=True)
    db_session.add(c1)
    await db_session.commit()

    picked = await _pick_node(db_session, "awg", None)
    assert picked.id == node2.id

    # Scenario 3: node2 is saturated (CPU > 70)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    stat2 = NodeStat(node_id=node2.id, cpu_ema=80.0, rx_bps=1000.0, tx_bps=1000.0, timestamp=now)
    db_session.add(stat2)
    await db_session.commit()

    picked = await _pick_node(db_session, "awg", None)
    assert picked.id == node1.id  # node2 has +100 penalty

    # Scenario 4: node1 has rising load, node2 is stable (but node2 still has saturation penalty)
    # Let's remove saturation from node2 first
    await db_session.delete(stat2)
    await db_session.commit()

    # node1: rising load (last 3 stats: 10, 20, 30)
    for i, cpu in enumerate([30.0, 20.0, 10.0]):  # stats[0] is newest
        s = NodeStat(
            node_id=node1.id,
            cpu_ema=cpu,
            rx_bps=1000.0,
            tx_bps=1000.0,
            timestamp=now - timedelta(minutes=i),
        )
        db_session.add(s)

    # node2: stable load (last 3 stats: 15, 15, 15)
    for i in range(3):
        s = NodeStat(
            node_id=node2.id,
            cpu_ema=15.0,
            rx_bps=1000.0,
            tx_bps=1000.0,
            timestamp=now - timedelta(minutes=i),
        )
        db_session.add(s)

    await db_session.commit()

    # node1 has 1 client (score 1) + rising trend (2 steps increase: +4) = score 5
    # node2 has 0 clients (score 0) + stable trend (+0) = score 0
    picked = await _pick_node(db_session, "awg", None)
    assert picked.id == node2.id

    # Scenario 5: both have same clients, but node2 has rising trend
    c2 = Client(external_id="c2", node_id=node2.id, is_active=True)
    db_session.add(c2)
    await db_session.commit()

    # node1 score: 1 client + 4 trend = 5
    # Let's make node2 trend worse: 10, 20, 30, 40, 50
    # Delete old node2 stats
    q = await db_session.execute(select(NodeStat).where(NodeStat.node_id == node2.id))
    for s in q.scalars().all():
        await db_session.delete(s)

    for i, cpu in enumerate([50.0, 40.0, 30.0, 20.0, 10.0]):
        s = NodeStat(
            node_id=node2.id,
            cpu_ema=cpu,
            rx_bps=1000.0,
            tx_bps=1000.0,
            timestamp=now - timedelta(minutes=i),
        )
        db_session.add(s)
    await db_session.commit()

    # node1: 1 client + 2 steps increase = 1 + 4 = 5
    # node2: 1 client + 4 steps increase = 1 + 8 = 9
    picked = await _pick_node(db_session, "awg", None)
    assert picked.id == node1.id
