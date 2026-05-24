from unittest.mock import patch

import pytest
from kosatka_master.models.client import Client
from kosatka_master.models.node import Node
from kosatka_master.services.chain_manager import ChainManager
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_provision_chain_success(db_session: AsyncSession):
    # Setup Exit Node
    exit_node = Node(
        name="exit-node",
        address="http://exit-agent",
        provider_type="wireguard",
        role="exit",
        is_active=True,
    )
    db_session.add(exit_node)
    await db_session.commit()
    await db_session.refresh(exit_node)

    # Setup Proxy Node linked to Exit Node
    proxy_node = Node(
        name="proxy-node",
        address="http://proxy-agent",
        provider_type="xray_relay",
        role="proxy",
        upstream_id=exit_node.id,
        is_active=True,
    )
    db_session.add(proxy_node)
    await db_session.commit()
    await db_session.refresh(proxy_node)

    client = Client(external_id="test-client", email="test@example.com")
    db_session.add(client)
    await db_session.commit()
    await db_session.refresh(client)

    chain_manager = ChainManager(db_session)

    with patch("kosatka_master.services.chain_manager._call_agent") as mock_call:
        # Mock responses for the sequence of calls:
        # 1. Exit Agent POST /clients -> returns config in POST body
        # 2. Proxy Agent POST /relays -> returns config in POST body
        mock_call.side_effect = [
            {"config_text": "wg-config-data", "address": "10.8.0.2", "public_key": "exit-pubkey"},
            {"config_text": "relayed-config-data", "status": "success"},
        ]

        result = await chain_manager.provision_chain(client, proxy_node, protocol="stealth")

        # The final config should come from the first node in the chain (the Proxy)
        assert result["config_text"] == "relayed-config-data"
        assert result["node_id"] == proxy_node.id
        # Public key should come from the Exit node
        assert result["public_key"] == "exit-pubkey"

        # Verify calls
        assert mock_call.call_count == 2
        # Exit agent call
        args, kwargs = mock_call.call_args_list[0]
        assert args[0].id == exit_node.id
        assert kwargs["json"]["external_id"] == "test-client"

        # Proxy agent call
        args, kwargs = mock_call.call_args_list[1]
        assert args[0].id == proxy_node.id
        assert kwargs["json"]["upstream_config"] == "wg-config-data"
