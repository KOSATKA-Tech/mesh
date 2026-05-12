from typing import Any, Dict, List

import httpx

from .base import BaseNodeProvider


class AgentNodeProvider(BaseNodeProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def get_nodes(self) -> List[Dict[str, Any]]:
        # This might be used if the agent provides a list of sub-nodes,
        # but usually it's one agent per node.
        return []

    async def sync_node(self, node_address: str) -> Dict[str, Any] | None:
        # The agent exposes `/health` (not `/api/v1/status`). Hitting a
        # non-existent path would mark every node offline forever.
        headers = {}
        if self.api_key:
            headers["X-Kosatka-Key"] = self.api_key

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{node_address.rstrip('/')}/health/",
                    headers=headers,
                    timeout=5.0,
                )
                if response.status_code == 200:
                    return response.json()
                return None
            except Exception:
                return None
