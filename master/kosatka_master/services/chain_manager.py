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

    async def provision_dynamic_relay(self, node: Node) -> Dict[str, Any]:
        """
        Generate and push a multi-upstream config to a relay node.
        """
        upstreams_ids = node.metadata_json.get("upstreams", [])
        if not upstreams_ids and node.upstream_id:
            upstreams_ids = [node.upstream_id]

        if not upstreams_ids:
            raise ChainError(f"Node {node.name} has no upstreams configured")

        upstream_nodes = []
        for uid in upstreams_ids:
            u_node = await self._get_node(uid)
            if not u_node:
                raise ChainError(f"Upstream node ID {uid} not found")
            upstream_nodes.append(u_node)

        config = self.generate_relay_config(node, upstream_nodes)

        # Push to agent
        try:
            return await _call_agent(node, "POST", "/relay/config", json=config)
        except Exception as e:
            raise ChainError(f"Failed to push config to agent {node.name}: {e}")

    def generate_relay_config(self, node: Node, upstreams: list[Node]) -> Dict[str, Any]:
        """
        Generate Xray config with multiple outbounds and urltest for failover.
        """
        outbounds = []
        outbound_tags = []

        for i, u_node in enumerate(upstreams):
            tag = f"upstream-{i + 1}"
            outbound_tags.append(tag)

            # Default values for KOSATKA Reality
            reality_pub = u_node.metadata_json.get("reality_public_key") or ""
            reality_dest = u_node.metadata_json.get("reality_dest") or "google.com:443"
            dest_host = reality_dest.split(":")[0]
            relay_uuid = (
                u_node.metadata_json.get("relay_uuid") or "00000000-0000-0000-0000-000000000000"
            )
            relay_port = u_node.metadata_json.get("relay_port") or 443

            outbounds.append(
                {
                    "tag": tag,
                    "protocol": "vless",
                    "settings": {
                        "vnext": [
                            {
                                "address": u_node.address.replace("http://", "")
                                .replace("https://", "")
                                .split(":")[0],
                                "port": int(relay_port),
                                "users": [{"id": relay_uuid, "encryption": "none"}],
                            }
                        ]
                    },
                    "streamSettings": {
                        "network": "tcp",
                        "security": "reality",
                        "realitySettings": {
                            "publicKey": reality_pub,
                            "fingerprint": "chrome",
                            "serverName": dest_host,
                            "shortId": u_node.metadata_json.get("reality_short_id") or "",
                        },
                    },
                }
            )

        # Add freedom outbound for direct fallback
        outbounds.append({"protocol": "freedom", "tag": "direct"})

        # Failover/Balancing outbound
        # We use 'urltest' to pick the fastest healthy upstream
        outbounds.insert(
            0,
            {
                "tag": "proxy-out",
                "protocol": "loopback",  # or just a tag alias
                "settings": {"outboundTag": outbound_tags[0]},  # Placeholder, replaced by balancer
            },
        )

        config = {
            "log": {"loglevel": "info"},
            "inbounds": [
                {
                    "tag": "socks-in",
                    "port": 1080,
                    "protocol": "socks",
                    "settings": {"auth": "noauth", "udp": True},
                }
            ],
            "outbounds": outbounds,
            "observatory": {
                "subjectSelector": outbound_tags,
                "probeUrl": "http://cp.cloudflare.com/generate_204",
                "probeInterval": "1m",
            },
            "routing": {
                "domainStrategy": "AsIs",
                "balancers": [
                    {
                        "tag": "balancer",
                        "selector": outbound_tags,
                        "strategy": {"type": "leastPing"},
                    }
                ],
                "rules": [{"type": "field", "balancerTag": "balancer", "port": "1-65535"}],
            },
        }
        return config
