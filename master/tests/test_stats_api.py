import pytest
from httpx import AsyncClient
from kosatka_master.models.node import Node, NodeStat


@pytest.mark.asyncio
async def test_get_realtime_stats(client: AsyncClient, db_session):
    # Create a node
    node = Node(
        name="test-node", address="1.1.1.1", provider_type="agent", is_active=True, status="online"
    )
    db_session.add(node)
    await db_session.commit()
    await db_session.refresh(node)

    # Create some stats
    for i in range(3):
        stat = NodeStat(node_id=node.id, cpu_ema=10.0 + i, rx_bps=100.0, tx_bps=200.0)
        db_session.add(stat)
    await db_session.commit()

    response = await client.get("/api/v1/stats/realtime", headers={"X-Kosatka-Key": "default-key"})
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert len(data["nodes"]) > 0
    assert data["nodes"][0]["name"] == "test-node"
    assert len(data["nodes"][0]["cpu_history"]) == 3
    assert data["nodes"][0]["cpu_history"] == [12.0, 11.0, 10.0]
