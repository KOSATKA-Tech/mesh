import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List

from ..bootstrap import bootstrap_provider, get_public_ip, run_command
from .base import BaseAgentProvider

logger = logging.getLogger(__name__)

SINGBOX_CONFIG_DIR = Path("/etc/sing-box")
SINGBOX_STATE_DIR = Path("/opt/kosatka/agent")
SINGBOX_CERT_PATH = SINGBOX_CONFIG_DIR / "cert.pem"
SINGBOX_KEY_PATH = SINGBOX_CONFIG_DIR / "key.pem"


class SingboxProvider(BaseAgentProvider):
    def __init__(self, protocol: str, port: int):
        self.protocol = protocol
        self.port = port
        self.config_path = SINGBOX_CONFIG_DIR / f"{protocol}.json"
        self.state_path = SINGBOX_STATE_DIR / f"{protocol}_peers.json"
        self.lock = asyncio.Lock()

    async def _ensure_bootstrapped(self):
        await bootstrap_provider("sing-box")
        SINGBOX_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        SINGBOX_STATE_DIR.mkdir(parents=True, exist_ok=True)

        if not SINGBOX_CERT_PATH.exists() or not SINGBOX_KEY_PATH.exists():
            logger.info("Generating self-signed certificate for sing-box TLS...")
            try:
                await run_command(
                    [
                        "openssl",
                        "req",
                        "-x509",
                        "-newkey",
                        "rsa:2048",
                        "-keyout",
                        str(SINGBOX_KEY_PATH),
                        "-out",
                        str(SINGBOX_CERT_PATH),
                        "-sha256",
                        "-days",
                        "3650",
                        "-nodes",
                        "-subj",
                        "/CN=kosatka-mesh",
                    ]
                )
            except Exception as e:
                logger.error(f"Failed to generate self-signed cert: {e}")

        if not self.config_path.exists():
            logger.info(f"Sing-box {self.protocol} config missing, bootstrapping...")
            config = await self._generate_base_config()
            self.config_path.write_text(json.dumps(config, indent=2))

        # Start/Restart sing-box
        # We'll use a simple process management for now, or systemd if available
        await self._restart_service()

    async def _restart_service(self):
        # In a real environment, we might use systemd.
        # For simplicity and Docker compatibility, we can try systemctl and fallback to direct execution
        # But for this task, let's assume systemd exists or we manage it via kosatka-agent.
        # Actually, let's use a simple background process for now if systemctl fails.
        try:
            await asyncio.create_subprocess_exec(
                "systemctl", "restart", f"sing-box-{self.protocol}"
            )
        except Exception:
            # Fallback: kill existing and start new
            logger.warning(
                f"Could not restart sing-box-{self.protocol} via systemctl, trying pkill"
            )
            try:
                await asyncio.create_subprocess_exec("pkill", "-f", f"sing-box.*{self.config_path}")
                await asyncio.sleep(1)
            except Exception:
                pass

            asyncio.create_subprocess_exec(
                "sing-box",
                "run",
                "-c",
                str(self.config_path),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )

    async def _generate_base_config(self) -> Dict[str, Any]:
        return {
            "log": {"level": "info"},
            "inbounds": [
                {
                    "type": self.protocol,
                    "tag": f"{self.protocol}-in",
                    "listen": "::",
                    "listen_port": self.port,
                    "users": [],
                    "tls": {
                        "enabled": True,
                        "certificate_path": str(SINGBOX_CERT_PATH),
                        "key_path": str(SINGBOX_KEY_PATH),
                    },
                }
            ],
            "outbounds": [{"type": "direct", "tag": "direct"}],
        }

    def _load_state(self) -> Dict[str, Any]:
        if not self.state_path.exists():
            return {"peers": {}}
        try:
            return json.loads(self.state_path.read_text())
        except Exception:
            return {"peers": {}}

    def _save_state(self, state: Dict[str, Any]):
        self.state_path.write_text(json.dumps(state, indent=2))

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

            password = client_data.get("password") or str(uuid.uuid4())
            user_uuid = str(uuid.uuid4())

            peer = {"id": client_id, "uuid": user_uuid, "password": password, "status": "added"}
            state["peers"][client_id] = peer
            self._save_state(state)

            config = json.loads(self.config_path.read_text())
            user_config = self._generate_user_config(peer)
            config["inbounds"][0]["users"].append(user_config)
            self.config_path.write_text(json.dumps(config, indent=2))

            await self._restart_service()
            return peer

    def _generate_user_config(self, peer: Dict[str, Any]) -> Dict[str, Any]:
        if self.protocol == "hysteria2":
            return {"password": peer["password"]}
        elif self.protocol == "tuic":
            return {"uuid": peer["uuid"], "password": peer["password"]}
        return {}

    async def delete_client(self, client_id: str) -> bool:
        async with self.lock:
            state = self._load_state()
            if client_id not in state["peers"]:
                return False

            peer = state["peers"].pop(client_id)
            self._save_state(state)

            config = json.loads(self.config_path.read_text())
            if self.protocol == "hysteria2":
                config["inbounds"][0]["users"] = [
                    u for u in config["inbounds"][0]["users"] if u["password"] != peer["password"]
                ]
            elif self.protocol == "tuic":
                config["inbounds"][0]["users"] = [
                    u for u in config["inbounds"][0]["users"] if u["uuid"] != peer["uuid"]
                ]

            self.config_path.write_text(json.dumps(config, indent=2))
            await self._restart_service()
            return True

    async def get_client_config(self, client_id: str) -> str:
        state = self._load_state()
        peer = state["peers"].get(client_id)
        if not peer:
            return ""
        ip = await get_public_ip()

        if self.protocol == "hysteria2":
            return (
                f"hysteria2://{peer['password']}@{ip}:{self.port}/?insecure=1#Kosatka-{client_id}"
            )
        elif self.protocol == "tuic":
            return f"tuic://{peer['uuid']}:{peer['password']}@{ip}:{self.port}/?congestion_control=bbr&alpn=h3&sni=google.com&udp_relay_mode=quic&allow_insecure=1#Kosatka-{client_id}"
        return ""

    async def get_client_stats(self, client_id: str) -> Dict[str, Any]:
        return {"id": client_id, "uplink": 0, "downlink": 0}


class Hysteria2Provider(SingboxProvider):
    def __init__(self, port: int = 443):
        super().__init__("hysteria2", port)


class TUICProvider(SingboxProvider):
    def __init__(self, port: int = 8443):
        super().__init__("tuic", port)
