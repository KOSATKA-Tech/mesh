from unittest.mock import AsyncMock, MagicMock

import pytest
from kosatka_master.models.client import Client
from kosatka_master.models.node import Node
from kosatka_master.services.chain_manager import ChainError, ChainManager


@pytest.mark.asyncio
async def test_resolve_full_chain_success():
    # Setup: A (relay) -> B (relay) -> C (exit)
    node_c = MagicMock(spec=Node, id=3, role="exit", upstream_id=None)
    node_b = MagicMock(spec=Node, id=2, role="relay", upstream_id=3)
    node_a = MagicMock(spec=Node, id=1, role="relay", upstream_id=2)

    mock_db = AsyncMock()
    manager = ChainManager(mock_db)

    # Mocking _get_node for traversal
    async def side_effect(node_id):
        return {2: node_b, 3: node_c}.get(node_id)

    manager._get_node = AsyncMock(side_effect=side_effect)

    chain = await manager.resolve_full_chain(node_a)
    assert [n.id for n in chain] == [1, 2, 3]


@pytest.mark.asyncio
async def test_resolve_full_chain_cycle():
    # Setup: A -> B -> A
    node_b = MagicMock(spec=Node, id=2, role="relay", upstream_id=1)
    node_a = MagicMock(spec=Node, id=1, role="relay", upstream_id=2)

    mock_db = AsyncMock()
    manager = ChainManager(mock_db)

    async def side_effect(node_id):
        return {1: node_a, 2: node_b}.get(node_id)

    manager._get_node = AsyncMock(side_effect=side_effect)

    with pytest.raises(ChainError, match="Cycle detected"):
        await manager.resolve_full_chain(node_a)


@pytest.mark.asyncio
async def test_resolve_full_chain_no_exit():
    # Setup: A -> B (relay, no upstream)
    node_b = MagicMock(spec=Node, id=2, name="node-b", role="relay", upstream_id=None)
    node_a = MagicMock(spec=Node, id=1, name="node-a", role="relay", upstream_id=2)

    mock_db = AsyncMock()
    manager = ChainManager(mock_db)

    async def side_effect(node_id):
        return {2: node_b}.get(node_id)

    manager._get_node = AsyncMock(side_effect=side_effect)

    with pytest.raises(ChainError, match="is not an exit node"):
        await manager.resolve_full_chain(node_a)


@pytest.mark.asyncio
async def test_provision_chain_multi_hop(mocker):
    # Setup: A -> B -> C (exit)
    node_c = MagicMock(
        spec=Node, id=3, name="node-c", role="exit", upstream_id=None, provider_type="awg"
    )
    node_b = MagicMock(
        spec=Node, id=2, name="node-b", role="relay", upstream_id=3, provider_type="relay"
    )
    node_a = MagicMock(
        spec=Node, id=1, name="node-a", role="relay", upstream_id=2, provider_type="relay"
    )

    client = MagicMock(spec=Client, id=10, external_id="client-123", email="test@example.com")

    mock_db = AsyncMock()
    manager = ChainManager(mock_db)

    # Mock resolve_full_chain
    manager.resolve_full_chain = AsyncMock(return_value=[node_a, node_b, node_c])

    # Mock _call_agent
    mock_call = mocker.patch(
        "kosatka_master.services.chain_manager._call_agent", new_callable=AsyncMock
    )

    # Return different results for each node
    async def call_side_effect(node, method, path, **kwargs):
        if node.id == 3:  # Exit node
            return {"config_text": "config-from-c", "address": "10.0.0.2", "public_key": "pub-c"}
        if node.id == 2:  # Relay B
            assert kwargs["json"]["upstream_config"] == "config-from-c"
            return {"config_text": "config-from-b"}
        if node.id == 1:  # Relay A
            assert kwargs["json"]["upstream_config"] == "config-from-b"
            return {"config_text": "config-from-a"}
        return {}

    mock_call.side_effect = call_side_effect

    result = await manager.provision_chain(client, node_a, "stealth-awg")

    # Verify order of calls: C -> B -> A
    assert mock_call.call_count == 3
    assert mock_call.call_args_list[0][0][0].id == 3
    assert mock_call.call_args_list[1][0][0].id == 2
    assert mock_call.call_args_list[2][0][0].id == 1

    assert result["config_text"] == "config-from-a"
    assert result["node_id"] == 1
