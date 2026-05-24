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


class ChainError(Exception):
    pass


class ChainManager:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_node(self, node_id: int) -> Node | None:
        res = await self.db.execute(select(Node).where(Node.id == node_id))
        return res.scalar_one_or_none()

    async def resolve_full_chain(self, start_node: Node) -> list[Node]:
        """
        Traverse upstream_id links from start_node to find the full path.
        Returns a list of Nodes starting with start_node.
        Raises ChainError on cycles, missing nodes, or if it doesn't end in an exit node.
        """
        chain = []
        visited = set()
        current = start_node

        while current:
            if current.id in visited:
                raise ChainError(f"Cycle detected at node {current.id}")

            chain.append(current)
            visited.add(current.id)

            if not current.upstream_id:
                if current.role != "exit":
                    raise ChainError(
                        f"Chain ends at node {current.name} (ID: {current.id}) "
                        f"which is not an exit node (role={current.role})"
                    )
                break

            upstream_id = current.upstream_id
            current = await self._get_node(upstream_id)
            if not current:
                raise ChainError(f"Upstream node ID {upstream_id} not found")

        return chain

    async def provision_chain(
        self, client: Client, start_node: Node, protocol: str
    ) -> Dict[str, Any]:
        """
        Provision a multi-hop chain:
        1. Resolve the full chain of nodes.
        2. Provision nodes in reverse (Exit node first via /clients, then Relays via /relays).
        3. The output config of one node becomes the upstream_config for the next.
        4. Return the final config for the start node.
        """
        chain = await self.resolve_full_chain(start_node)

        current_config = ""
        exit_result: Dict[str, Any] = {}

        for node in reversed(chain):
            if node.role == "exit":
                # Exit node: POST /clients
                payload = {"external_id": client.external_id, "email": client.email}
                res = await _call_agent(node, "POST", "/clients", json=payload)
                current_config = res.get("config_text") or ""
                if not current_config:
                    # Fallback if config was not in POST response
                    try:
                        follow_up = await _call_agent(
                            node, "GET", f"/clients/{client.external_id}/config"
                        )
                        current_config = follow_up.get("config", "")
                    except HTTPException:
                        current_config = ""
                exit_result = res
            else:
                # Relay node: POST /relays
                relay_payload = {
                    "external_id": client.external_id,
                    "upstream_config": current_config,
                }
                res = await _call_agent(node, "POST", "/relays", json=relay_payload)
                current_config = res.get("config_text") or ""
                if not current_config and node.id == start_node.id:
                    # For the start node, we really need the config.
                    # Relays might also support /clients/{id}/config if they share logic.
                    try:
                        follow_up = await _call_agent(
                            node, "GET", f"/clients/{client.external_id}/config"
                        )
                        current_config = follow_up.get("config", "")
                    except HTTPException:
                        pass

        # Return merged results.
        return {
            "config_text": current_config,
            "node_id": start_node.id,
            "address": exit_result.get("address"),
            "public_key": exit_result.get("public_key"),
        }
