"""``NodeManager.sync_all_nodes`` is on the scheduler hot path.

Probing agents serially used to multiply the worst-case sync latency
by N \u2014 with default ``KOSATKA_SYNC_INTERVAL=60`` and a single
slow/dead node, ten nodes alone could blow past the next tick. PR #5
parallelised the loop with ``asyncio.gather(...)``; this test pins
that contract and the exception-tolerance behaviour.
"""

import asyncio
import uuid
from datetime import datetime
from unittest.mock import patch

import pytest
from kosatka_master.models.node import Node
from kosatka_master.services.node_manager import NodeManager


@pytest.mark.asyncio
async def test_sync_all_nodes_runs_probes_concurrently(db_session):
    # Unique name prefix so this test doesn't collide on
    # ``UNIQUE(nodes.name)`` with state left behind by other tests on
    # the session-scoped sqlite fixture.
    tag = uuid.uuid4().hex[:8]
    for i in range(3):
        node = Node(
            name=f"parallel-{tag}-{i}",
            address=f"http://10.{tag[:2]}.0.{i + 1}:8000",
            provider_type="agent",
            is_active=True,
            api_key=f"key-{i}",
        )
        db_session.add(node)
    await db_session.commit()

    in_flight = 0
    max_in_flight = 0

    async def fake_sync_node(self, address):
        nonlocal in_flight, max_in_flight
        in_flight += 1
        max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0.02)
        in_flight -= 1
        return True

    manager = NodeManager(db_session)
    with patch(
        "kosatka_master.services.providers.agent_provider.AgentNodeProvider.sync_node",
        new=fake_sync_node,
    ):
        await manager.sync_all_nodes()

    # Serial execution would peg max_in_flight at 1 regardless of node
    # count. The session-scoped sqlite fixture might have other active
    # nodes left behind by sibling tests, so assert "more than one in
    # flight" rather than an exact count.
    assert max_in_flight >= 2, (
        f"sync_all_nodes should probe nodes concurrently; observed peak "
        f"in-flight={max_in_flight} (serial loop would observe 1)"
    )


@pytest.mark.asyncio
async def test_sync_all_nodes_one_failing_does_not_break_others(db_session):
    tag = uuid.uuid4().hex[:8]
    flaky_addr = f"http://192.168.{int(tag[:2], 16)}.2:8000"
    addresses = [
        f"http://192.168.{int(tag[:2], 16)}.1:8000",
        flaky_addr,
        f"http://192.168.{int(tag[:2], 16)}.3:8000",
    ]
    nodes = []
    for i, addr in enumerate(addresses):
        node = Node(
            name=f"flaky-{tag}-{i}",
            address=addr,
            provider_type="agent",
            is_active=True,
            api_key=f"key-{i}",
        )
        db_session.add(node)
        nodes.append(node)
    await db_session.commit()

    async def flaky(self, address):
        if address == flaky_addr:
            raise RuntimeError("agent unreachable")
        return {"status": "ok", "provider": "agent"}

    manager = NodeManager(db_session)
    with patch(
        "kosatka_master.services.providers.agent_provider.AgentNodeProvider.sync_node",
        new=flaky,
    ):
        await manager.sync_all_nodes()

    statuses = {n.address: n.status for n in nodes}
    assert statuses[addresses[0]] == "online"
    assert statuses[flaky_addr] == "offline"  # raised \u2192 marked offline.
    assert statuses[addresses[2]] == "online"
    for n in nodes:
        assert isinstance(n.last_seen, datetime)
