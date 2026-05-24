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
        self.url = (url or "http://localhost:8000").rstrip("/")
        self.username = username or "admin"
        self.password = password or "admin"
        self.token = None
        self.lock = asyncio.Lock()

    async def _ensure_bootstrapped(self):
        # Local bootstrap only if using localhost and directory doesn't exist
        if "localhost" in self.url and not MARZBAN_DIR.exists():
            logger.info("Marzban local instance missing, bootstrapping...")
            await bootstrap_provider("marzban")

            MARZBAN_DIR.mkdir(parents=True, exist_ok=True)
            try:
                await run_command(
                    [
                        "git",
                        "clone",
                        "https://github.com/Gozargah/Marzban-docker.git",
                        str(MARZBAN_DIR),
                    ]
                )

                # Setup .env
                env_content = f"SUDO_USERNAME={self.username}\nSUDO_PASSWORD={self.password}\n"
                (MARZBAN_DIR / ".env").write_text(env_content)

                await run_command(
                    ["docker", "compose", "-f", str(MARZBAN_DIR / "docker-compose.yml"), "up", "-d"]
                )
                # Wait for it to start
                await asyncio.sleep(15)
            except Exception as exc:
                logger.error(f"Failed to bootstrap Marzban: {exc}")
                raise

    async def _get_token(self):
        if self.token:
            return self.token

        await self._ensure_bootstrapped()

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(
                    f"{self.url}/api/admin/token",
                    data={"username": self.username, "password": self.password},
                )
                resp.raise_for_status()
                self.token = resp.json()["access_token"]
                return self.token
            except Exception as exc:
                logger.error(f"Failed to get Marzban token from {self.url}: {exc}")
                raise

    async def get_clients(self) -> List[Dict[str, Any]]:
        token = await self._get_token()
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(
                    f"{self.url}/api/users", headers={"Authorization": f"Bearer {token}"}
                )
                resp.raise_for_status()
                users = resp.json().get("users", [])
                return [{"client_id": u["username"], "status": u["status"]} for u in users]
            except Exception as exc:
                logger.error(f"Failed to fetch users from Marzban: {exc}")
                return []

    async def get_client(self, client_id: str) -> Dict[str, Any] | None:
        token = await self._get_token()
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(
                    f"{self.url}/api/user/{client_id}", headers={"Authorization": f"Bearer {token}"}
                )
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                u = resp.json()
                return {"client_id": u["username"], "status": u["status"]}
            except Exception as exc:
                logger.error(f"Failed to fetch user {client_id} from Marzban: {exc}")
                return None

    async def create_client(self, client_data: Dict[str, Any]) -> Dict[str, Any]:
        async with self.lock:
            token = await self._get_token()
            client_id = str(
                client_data.get("external_id")
                or client_data.get("id")
                or client_data.get("username")
            )

            # Check if exists
            existing = await self.get_client(client_id)
            if existing:
                return existing

            async with httpx.AsyncClient(timeout=15.0) as client:
                try:
                    # Minimal user creation for Xray/VLESS
                    payload = {"username": client_id, "proxies": {"vless": {}}, "inbounds": {}}
                    resp = await client.post(
                        f"{self.url}/api/user",
                        json=payload,
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    resp.raise_for_status()
                    u = resp.json()
                    return {
                        "id": u["username"],
                        "client_id": u["username"],
                        "status": "created",
                        "config_text": u.get("subscription_url", ""),
                    }
                except Exception as exc:
                    logger.error(f"Failed to create user {client_id} in Marzban: {exc}")
                    raise

    async def delete_client(self, client_id: str) -> bool:
        token = await self._get_token()
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.delete(
                    f"{self.url}/api/user/{client_id}", headers={"Authorization": f"Bearer {token}"}
                )
                return resp.status_code == 200
            except Exception as exc:
                logger.error(f"Failed to delete user {client_id} from Marzban: {exc}")
                return False

    async def get_client_config(self, client_id: str) -> str:
        token = await self._get_token()
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(
                    f"{self.url}/api/user/{client_id}", headers={"Authorization": f"Bearer {token}"}
                )
                if resp.status_code == 404:
                    return ""
                resp.raise_for_status()
                return resp.json().get("subscription_url", "")
            except Exception as exc:
                logger.error(f"Failed to get config for user {client_id} from Marzban: {exc}")
                return ""

    async def get_client_stats(self, client_id: str) -> Dict[str, Any]:
        token = await self._get_token()
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(
                    f"{self.url}/api/user/{client_id}", headers={"Authorization": f"Bearer {token}"}
                )
                if resp.status_code != 200:
                    return {"usage": 0}
                u = resp.json()
                return {
                    "used_traffic": u.get("used_traffic", 0),
                    "lifetime_used_traffic": u.get("lifetime_used_traffic", 0),
                }
            except Exception:
                return {"usage": 0}
