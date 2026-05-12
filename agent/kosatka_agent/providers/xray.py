import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from ..bootstrap import bootstrap_provider, get_public_ip
from .base import BaseAgentProvider

logger = logging.getLogger(__name__)

XRAY_CONFIG_DIR = Path("/etc/xray")
XRAY_CONFIG_PATH = XRAY_CONFIG_DIR / "config.json"
XRAY_STATE_PATH = Path("/opt/kosatka/agent/xray_peers.json")


class XrayProvider(BaseAgentProvider):
    def __init__(self):
        self.lock = asyncio.Lock()

    async def _ensure_bootstrapped(self):
        await bootstrap_provider("xray")
        if not XRAY_CONFIG_PATH.exists():
            logger.info("Xray config missing, bootstrapping...")
            XRAY_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

            await get_public_ip()
            config = {
                "inbounds": [
                    {
                        "port": 443,
                        "protocol": "vless",
                        "settings": {"clients": [], "decryption": "none"},
                        "streamSettings": {"network": "tcp", "security": "none"},
                    }
                ],
                "outbounds": [{"protocol": "freedom"}],
            }
            XRAY_CONFIG_PATH.write_text(json.dumps(config, indent=2))

        # Ensure xray is running (best effort)
        # In a real setup, this might be a systemd service or background proc
        try:
            await asyncio.create_subprocess_exec("systemctl", "restart", "xray")
        except Exception:
            pass

    def _load_state(self) -> Dict[str, Any]:
        if not XRAY_STATE_PATH.exists():
            return {"peers": {}}
        return json.loads(XRAY_STATE_PATH.read_text())

    def _save_state(self, state: Dict[str, Any]):
        XRAY_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        XRAY_STATE_PATH.write_text(json.dumps(state, indent=2))

    async def get_clients(self) -> List[Dict[str, Any]]:
        state = self._load_state()
        return list(state["peers"].values())

    async def get_client(self, client_id: str) -> Dict[str, Any] | None:
        state = self._load_state()
        return state["peers"].get(client_id)

    async def create_client(self, client_data: Dict[str, Any]) -> Dict[str, Any]:
        async with self.lock:
            await self._ensure_bootstrapped()
            state = self._load_state()

            client_id = str(client_data.get("external_id") or client_data.get("id"))
            if client_id in state["peers"]:
                return state["peers"][client_id]

            import uuid

            user_uuid = str(uuid.uuid4())
            peer = {"id": client_id, "uuid": user_uuid, "status": "added"}
            state["peers"][client_id] = peer
            self._save_state(state)

            # Update Xray config
            config = json.loads(XRAY_CONFIG_PATH.read_text())
            config["inbounds"][0]["settings"]["clients"].append(
                {"id": user_uuid, "email": f"{client_id}@kosatka.mesh"}
            )
            XRAY_CONFIG_PATH.write_text(json.dumps(config, indent=2))

            # Restart Xray
            try:
                await asyncio.create_subprocess_exec("systemctl", "reload", "xray")
            except Exception:
                pass

            return peer

    async def delete_client(self, client_id: str) -> bool:
        async with self.lock:
            state = self._load_state()
            if client_id not in state["peers"]:
                return False

            peer = state["peers"].pop(client_id)
            self._save_state(state)

            config = json.loads(XRAY_CONFIG_PATH.read_text())
            config["inbounds"][0]["settings"]["clients"] = [
                c for c in config["inbounds"][0]["settings"]["clients"] if c["id"] != peer["uuid"]
            ]
            XRAY_CONFIG_PATH.write_text(json.dumps(config, indent=2))

            try:
                await asyncio.create_subprocess_exec("systemctl", "reload", "xray")
            except Exception:
                pass
            return True

    async def get_client_config(self, client_id: str) -> str:
        state = self._load_state()
        peer = state["peers"].get(client_id)
        if not peer:
            return ""
        ip = await get_public_ip()
        return f"vless://{peer['uuid']}@{ip}:443?encryption=none&security=none&type=tcp#Kosatka-{client_id}"

    async def get_client_stats(self, client_id: str) -> Dict[str, Any]:
        return {"id": client_id, "up": 0, "down": 0}
