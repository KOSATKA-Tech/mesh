import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseAgentProvider

logger = logging.getLogger(__name__)

XRAY_CONFIG_DIR = Path("/etc/xray")
XRAY_RELAY_CONFIG_PATH = XRAY_CONFIG_DIR / "relay_config.json"


class XrayRelayProvider(BaseAgentProvider):
    def __init__(self, settings: Any):
        self.settings = settings
        self.process: Optional[asyncio.subprocess.Process] = None

    def generate_config(self) -> Dict[str, Any]:
        if self.settings.node_role == "exit":
            return self._generate_exit_config()
        elif self.settings.node_role == "proxy":
            return self._generate_proxy_config()
        else:
            return {}

    def _generate_exit_config(self) -> Dict[str, Any]:
        dest_host = self.settings.reality_dest.split(":")[0]
        return {
            "log": {"loglevel": "info"},
            "inbounds": [
                {
                    "tag": "vless-in",
                    "port": self.settings.relay_port,
                    "protocol": "vless",
                    "settings": {
                        "clients": (
                            [{"id": self.settings.relay_uuid, "email": "relay@kosatka.mesh"}]
                            if self.settings.relay_uuid
                            else []
                        ),
                        "decryption": "none",
                    },
                    "streamSettings": {
                        "network": "tcp",
                        "security": "reality",
                        "realitySettings": {
                            "show": False,
                            "dest": self.settings.reality_dest,
                            "xver": 0,
                            "serverNames": [dest_host],
                            "privateKey": self.settings.reality_private_key,
                            "shortIds": (
                                [self.settings.reality_short_id]
                                if self.settings.reality_short_id
                                else []
                            ),
                        },
                    },
                }
            ],
            "outbounds": [{"protocol": "freedom", "tag": "direct"}],
        }

    def _generate_proxy_config(self) -> Dict[str, Any]:
        dest_host = self.settings.reality_dest.split(":")[0]
        return {
            "log": {"loglevel": "info"},
            "inbounds": [
                {
                    "tag": "socks-in",
                    "port": 1080,
                    "protocol": "socks",
                    "settings": {"auth": "noauth", "udp": True},
                }
            ],
            "outbounds": [
                {
                    "tag": "proxy-out",
                    "protocol": "vless",
                    "settings": {
                        "vnext": [
                            {
                                "address": self.settings.upstream_address,
                                "port": self.settings.relay_port,
                                "users": (
                                    [{"id": self.settings.relay_uuid, "encryption": "none"}]
                                    if self.settings.relay_uuid
                                    else []
                                ),
                            }
                        ]
                    },
                    "streamSettings": {
                        "network": "tcp",
                        "security": "reality",
                        "realitySettings": {
                            "publicKey": self.settings.reality_public_key,
                            "fingerprint": "chrome",
                            "serverName": dest_host,
                            "shortId": self.settings.reality_short_id or "",
                        },
                    },
                },
                {"protocol": "freedom", "tag": "direct"},
            ],
            "routing": {
                "domainStrategy": "AsIs",
                "rules": [{"type": "field", "outboundTag": "proxy-out", "port": "1-65535"}],
            },
        }

    async def start(self):
        # If config doesn't exist, try to generate it from settings (legacy mode)
        if not XRAY_RELAY_CONFIG_PATH.exists():
            config = self.generate_config()
            if not config:
                logger.info("No config generated for XrayRelayProvider, skipping start")
                return
            XRAY_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            XRAY_RELAY_CONFIG_PATH.write_text(json.dumps(config, indent=2))

        bin_path = Path(self.settings.bin_path) / "xray"
        if not bin_path.exists():
            logger.error(f"Xray binary not found at {bin_path}")
            return

        logger.info(f"Starting Xray Relay from {bin_path} with role {self.settings.node_role}")
        self.process = await asyncio.create_subprocess_exec(
            str(bin_path),
            "run",
            "-c",
            str(XRAY_RELAY_CONFIG_PATH),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

    async def stop(self):
        if self.process:
            logger.info("Stopping Xray Relay")
            try:
                self.process.terminate()
                # Use wait() with timeout to ensure it stops
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    self.process.kill()
                    await self.process.wait()
            except Exception as e:
                logger.error(f"Error stopping Xray Relay: {e}")
            self.process = None

    async def update_config(self, config_dict: Dict[str, Any]):
        """Write new config and restart the process."""
        logger.info("Updating Xray Relay configuration")
        XRAY_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        XRAY_RELAY_CONFIG_PATH.write_text(json.dumps(config_dict, indent=2))
        await self.restart()

    async def restart(self):
        """Restart the Xray process."""
        logger.info("Restarting Xray Relay")
        await self.stop()
        await self.start()

    async def get_clients(self) -> List[Dict[str, Any]]:
        return []

    async def get_client(self, client_id: str) -> Dict[str, Any] | None:
        return None

    async def create_client(self, client_data: Dict[str, Any]) -> Dict[str, Any]:
        return {}

    async def delete_client(self, client_id: str) -> bool:
        return True

    async def get_client_config(self, client_id: str) -> str:
        return ""

    async def get_client_stats(self, client_id: str) -> Dict[str, Any]:
        return {}
