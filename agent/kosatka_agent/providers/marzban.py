import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List

import httpx

from ..bootstrap import bootstrap_provider, run_command
from .base import BaseAgentProvider

logger = logging.getLogger(__name__)

MARZBAN_DIR = Path("/opt/marzban")


class MarzbanProvider(BaseAgentProvider):
    def __init__(
        self, url: str | None = None, username: str | None = None, password: str | None = None
    ):
        self.url = url or "http://localhost:8000"
        self.username = username or "admin"
        self.password = password or "admin"
        self.token = None
        self.lock = asyncio.Lock()

    async def _ensure_bootstrapped(self):
        if self.url == "http://localhost:8000" and not MARZBAN_DIR.exists():
            logger.info("Marzban not found at localhost:8000, bootstrapping local instance...")
            await bootstrap_provider("marzban")

            MARZBAN_DIR.mkdir(parents=True, exist_ok=True)
            # Minimal bootstrap: clone marzban-docker or similar
            # For simplicity, we assume the user might want a quick setup
            await run_command(
                ["git", "clone", "https://github.com/Gozargah/Marzban-docker.git", str(MARZBAN_DIR)]
            )

            # Setup .env
            env_content = f"SUDO_USERNAME={self.username}\nSUDO_PASSWORD={self.password}\n"
            (MARZBAN_DIR / ".env").write_text(env_content)

            await run_command(
                ["docker", "compose", "-f", str(MARZBAN_DIR / "docker-compose.yml"), "up", "-d"]
            )
            # Wait for it to start
            await asyncio.sleep(10)

    async def _get_token(self):
        if self.token:
            return self.token
        await self._ensure_bootstrapped()
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self.url}/api/admin/token",
                    data={"username": self.username, "password": self.password},
                )
                resp.raise_for_status()
                self.token = resp.json()["access_token"]
                return self.token
            except Exception as exc:
                logger.error(f"Failed to get Marzban token: {exc}")
                raise

    async def get_clients(self) -> List[Dict[str, Any]]:
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.url}/api/users", headers={"Authorization": f"Bearer {token}"}
            )
            resp.raise_for_status()
            users = resp.json().get("users", [])
            return [{"client_id": u["username"], "status": u["status"]} for u in users]

    async def get_client(self, client_id: str) -> Dict[str, Any] | None:
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.url}/api/user/{client_id}", headers={"Authorization": f"Bearer {token}"}
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            u = resp.json()
            return {"client_id": u["username"], "status": u["status"]}

    async def create_client(self, client_data: Dict[str, Any]) -> Dict[str, Any]:
        token = await self._get_token()
        client_id = str(client_data.get("external_id") or client_data.get("id"))

        async with httpx.AsyncClient() as client:
            # Check if exists
            existing = await self.get_client(client_id)
            if existing:
                return existing

            resp = await client.post(
                f"{self.url}/api/user",
                json={"username": client_id, "proxies": {"vless": {}}, "inbounds": {}},
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            u = resp.json()
            return {
                "id": u["username"],
                "status": "created",
                "config_text": u.get("subscription_url", ""),
            }

    async def delete_client(self, client_id: str) -> bool:
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            resp = await client.delete(
                f"{self.url}/api/user/{client_id}", headers={"Authorization": f"Bearer {token}"}
            )
            return resp.status_code == 200

    async def get_client_config(self, client_id: str) -> str:
        client = await self.get_client(client_id)
        if not client:
            return ""
        token = await self._get_token()
        async with httpx.AsyncClient() as client_http:
            resp = await client_http.get(
                f"{self.url}/api/user/{client_id}", headers={"Authorization": f"Bearer {token}"}
            )
            resp.raise_for_status()
            return resp.json().get("subscription_url", "")

    async def get_client_stats(self, client_id: str) -> Dict[str, Any]:
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.url}/api/user/{client_id}/usage",
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code != 200:
                return {"usage": 0}
            return {"usage": resp.json().get("usage", 0)}
