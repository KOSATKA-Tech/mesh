from typing import Any, Dict, List, Optional

import httpx
from kosatka_master.http_client import get_global_httpx_client

from .base import BaseNodeProvider


class AgentNodeProvider(BaseNodeProvider):
    def __init__(self, api_key: str, client: Optional[httpx.AsyncClient] = None):
        self.api_key = api_key
        self.client = client

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

        client = self.client or await get_global_httpx_client()
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
