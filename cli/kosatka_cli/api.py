from typing import Any, Dict, List

import httpx

from .config import load_config


class APIClient:
    def __init__(self):
        self.config = load_config()
        self.headers = {
            "Content-Type": "application/json",
        }
        if self.config.api_key:
            self.headers["X-Kosatka-Key"] = self.config.api_key

    def _get_url(self, path: str) -> str:
        return f"{self.config.base_url.rstrip('/')}/api/v1{path}"

    async def request(self, method: str, path: str, **kwargs) -> Any:
        if not self.headers.get("X-Kosatka-Key"):
            raise ValueError(
                "No API key found. Please login first using: kosatka-mesh login <your-master-key>"
            )
        url = self._get_url(path)
        async with httpx.AsyncClient(headers=self.headers, follow_redirects=True) as client:
            response = await client.request(method, url, timeout=10.0, **kwargs)
            response.raise_for_status()
            return response.json()

    async def list_nodes(self) -> List[Dict[str, Any]]:
        return await self.request("GET", "/nodes/")

    async def register_node(
        self, name: str, address: str, provider_type: str = "agent", api_key: str | None = None
    ) -> Dict[str, Any]:
        data = {
            "name": name,
            "address": address,
            "provider_type": provider_type,
            "api_key": api_key,
        }
        return await self.request("POST", "/nodes/", json=data)

    async def provision_client(self, external_id: str, protocol: str) -> Dict[str, Any]:
        data = {"external_id": external_id, "protocol": protocol}
        return await self.request("POST", "/clients/provision/", json=data)

    async def get_node_health(self, node_id: int) -> Dict[str, Any]:
        return await self.request("GET", f"/nodes/{node_id}/health/")

    async def get_stats(self) -> Dict[str, Any]:
        return await self.request("GET", "/stats/summary/")
