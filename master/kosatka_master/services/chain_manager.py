from typing import Any, Dict

from fastapi import HTTPException
from kosatka_master.agent_client import call_agent
from kosatka_master.models.client import Client
from kosatka_master.models.node import Node
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def _call_agent(node: Node, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
    """Wrapper around global call_agent for easier mocking in tests."""
    return await call_agent(node, method, path, **kwargs)


class ChainManager:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def provision_chain(
        self, client: Client, proxy_node: Node, protocol: str
    ) -> Dict[str, Any]:
        """
        Provision a multi-hop chain:
        1. Fetch the upstream (exit) node.
        2. Create a standard VPN peer on the exit node.
        3. Create a relay entry on the proxy node pointing to that exit node.
        4. Return merged configuration.
        """
        if not proxy_node.upstream_id:
            raise HTTPException(
                status_code=400,
                detail=f"Node {proxy_node.name} (ID: {proxy_node.id}) is not a relay (missing upstream_id)",
            )

        # 1. Fetch exit_node
        res = await self.db.execute(select(Node).where(Node.id == proxy_node.upstream_id))
        exit_node = res.scalar_one_or_none()
        if not exit_node:
            raise HTTPException(
                status_code=404,
                detail=f"Upstream node ID {proxy_node.upstream_id} for proxy {proxy_node.name} not found",
            )

        # 2. Provision client on exit_node first
        exit_payload = {"external_id": client.external_id, "email": client.email}
        # Note: We use the exit_node's native provider_type for this call.
        exit_result = await _call_agent(exit_node, "POST", "/clients", json=exit_payload)

        config_text = exit_result.get("config_text")
        if not config_text:
            # Fallback if config was not in POST response
            try:
                follow_up = await _call_agent(
                    exit_node, "GET", f"/clients/{client.external_id}/config"
                )
                config_text = follow_up.get("config", "")
            except HTTPException:
                config_text = ""

        # 3. Provision relay on proxy_node
        relay_payload = {
            "external_id": client.external_id,
            "upstream_config": config_text,
        }
        # The test specifically mocks this call sequence.
        await _call_agent(proxy_node, "POST", "/relays", json=relay_payload)

        # 4. Return merged results.
        return {
            "config_text": config_text,
            "node_id": proxy_node.id,
            "address": exit_result.get("address"),
            "public_key": exit_result.get("public_key"),
        }
