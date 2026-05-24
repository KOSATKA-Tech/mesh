import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List

from ..bootstrap import bootstrap_provider, get_public_ip, run_command
from ..config import settings
from .base import BaseAgentProvider

logger = logging.getLogger(__name__)

SINGBOX_CONFIG_DIR = Path("/etc/sing-box")
SINGBOX_STATE_DIR = Path("/opt/kosatka/agent")
SINGBOX_CERT_PATH = SINGBOX_CONFIG_DIR / "cert.pem"
SINGBOX_KEY_PATH = SINGBOX_CONFIG_DIR / "key.pem"
SINGBOX_WG_KEY_PATH = SINGBOX_CONFIG_DIR / "wg_private.key"


class SingboxProvider(BaseAgentProvider):
    def __init__(self):
        self.config_path = SINGBOX_CONFIG_DIR / "config.json"
        self.state_path = SINGBOX_STATE_DIR / "singbox_peers.json"
        self.lock = asyncio.Lock()

        # Default ports
        self.reality_port = 443
        self.hysteria_port = 443
        self.tuic_port = 8443
        self.wg_port = 51820

    async def _ensure_bootstrapped(self):
        await bootstrap_provider("sing-box")
        SINGBOX_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        SINGBOX_STATE_DIR.mkdir(parents=True, exist_ok=True)

        # Generate TLS certs if missing
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

        # Generate WireGuard private key if missing
        if not SINGBOX_WG_KEY_PATH.exists():
            logger.info("Generating WireGuard private key for sing-box...")
            try:
                # We can use sing-box to generate wg key or just openssl/head
                # sing-box generate wg-key
                proc = await asyncio.create_subprocess_exec(
                    "sing-box",
                    "generate",
                    "wg-key",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await proc.communicate()
                if proc.returncode == 0:
                    SINGBOX_WG_KEY_PATH.write_text(stdout.decode().strip())
                else:
                    # Fallback if sing-box is not in path yet
                    import base64
                    import secrets

                    key = base64.b64encode(secrets.token_bytes(32)).decode()
                    SINGBOX_WG_KEY_PATH.write_text(key)
            except Exception as e:
                logger.error(f"Failed to generate WG key: {e}")

        if not self.config_path.exists():
            logger.info("Sing-box unified config missing, bootstrapping...")
            config = await self._generate_base_config()
            self.config_path.write_text(json.dumps(config, indent=2))

        await self._restart_service()

    async def _restart_service(self):
        try:
            # Check if systemd service exists, if not use pkill/start
            proc = await asyncio.create_subprocess_exec(
                "systemctl",
                "is-active",
                "sing-box",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            if proc.returncode == 0:
                await asyncio.create_subprocess_exec("systemctl", "restart", "sing-box")
            else:
                raise RuntimeError("systemd service not active")
        except Exception:
            logger.warning("Could not restart sing-box via systemctl, trying pkill")
            try:
                await asyncio.create_subprocess_exec("pkill", "-f", "sing-box.*config.json")
                await asyncio.sleep(0.5)
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
        wg_private_key = (
            SINGBOX_WG_KEY_PATH.read_text().strip() if SINGBOX_WG_KEY_PATH.exists() else ""
        )

        reality_private_key = settings.reality_private_key or ""
        # If reality_private_key is missing, Reality won't work properly, but we'll still add the inbound

        return {
            "log": {"level": "info"},
            "inbounds": [
                {
                    "type": "vless",
                    "tag": "vless-in",
                    "listen": "::",
                    "listen_port": self.reality_port,
                    "users": [],
                    "tls": {
                        "enabled": True,
                        "server_name": settings.reality_dest.split(":")[0],
                        "reality": {
                            "enabled": True,
                            "handshake": {
                                "server": settings.reality_dest.split(":")[0],
                                "server_port": (
                                    int(settings.reality_dest.split(":")[1])
                                    if ":" in settings.reality_dest
                                    else 443
                                ),
                            },
                            "private_key": reality_private_key,
                            "short_id": (
                                [settings.reality_short_id] if settings.reality_short_id else [""]
                            ),
                        },
                    },
                },
                {
                    "type": "hysteria2",
                    "tag": "hysteria2-in",
                    "listen": "::",
                    "listen_port": self.hysteria_port,
                    "users": [],
                    "ignore_client_bandwidth": True,
                    "tls": {
                        "enabled": True,
                        "certificate_path": str(SINGBOX_CERT_PATH),
                        "key_path": str(SINGBOX_KEY_PATH),
                    },
                },
                {
                    "type": "tuic",
                    "tag": "tuic-in",
                    "listen": "::",
                    "listen_port": self.tuic_port,
                    "users": [],
                    "tls": {
                        "enabled": True,
                        "certificate_path": str(SINGBOX_CERT_PATH),
                        "key_path": str(SINGBOX_KEY_PATH),
                    },
                },
                {
                    "type": "wireguard",
                    "tag": "wireguard-in",
                    "listen": "::",
                    "listen_port": self.wg_port,
                    "peers": [],
                    "local_address": ["10.10.10.1/24"],
                    "private_key": wg_private_key,
                    "mtu": 1420,
                },
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

            # WireGuard peer info
            # We need to generate a client private key if not provided
            # and assign an IP
            used_ips = {p.get("wg_ip") for p in state["peers"].values() if p.get("wg_ip")}
            for i in range(2, 254):
                ip = f"10.10.10.{i}"
                if ip not in used_ips:
                    wg_ip = ip
                    break
            else:
                wg_ip = "10.10.10.254"  # Fallback

            # In a real scenario, we'd use 'sing-box generate wg-key' for client too
            # or just rely on the master to provide the public key.
            # But here we'll generate if missing.
            client_wg_priv = client_data.get("wg_private_key")
            client_wg_pub = client_data.get("wg_public_key")

            if not client_wg_pub and not client_wg_priv:
                # Generate new pair
                proc = await asyncio.create_subprocess_exec(
                    "sing-box",
                    "generate",
                    "wg-key",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await proc.communicate()
                client_wg_priv = stdout.decode().strip()

                # Derive public key
                proc = await asyncio.create_subprocess_exec(
                    "sing-box",
                    "generate",
                    "wg-key",
                    "-p",
                    client_wg_priv,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await proc.communicate()
                client_wg_pub = stdout.decode().strip()

            peer = {
                "id": client_id,
                "uuid": user_uuid,
                "password": password,
                "wg_ip": wg_ip,
                "wg_public_key": client_wg_pub,
                "wg_private_key": client_wg_priv,
                "status": "added",
            }
            state["peers"][client_id] = peer
            self._save_state(state)

            # Update config
            config = json.loads(self.config_path.read_text())
            for inbound in config["inbounds"]:
                if inbound["type"] == "vless":
                    inbound["users"].append({"uuid": user_uuid, "flow": "xtls-rprx-vision"})
                elif inbound["type"] == "hysteria2":
                    inbound["users"].append({"password": password})
                elif inbound["type"] == "tuic":
                    inbound["users"].append({"uuid": user_uuid, "password": password})
                elif inbound["type"] == "wireguard":
                    inbound["peers"].append(
                        {"public_key": client_wg_pub, "allowed_ips": [f"{wg_ip}/32"]}
                    )

            self.config_path.write_text(json.dumps(config, indent=2))
            await self._restart_service()
            return peer

    async def delete_client(self, client_id: str) -> bool:
        async with self.lock:
            state = self._load_state()
            if client_id not in state["peers"]:
                return False

            peer = state["peers"].pop(client_id)
            self._save_state(state)

            config = json.loads(self.config_path.read_text())
            for inbound in config["inbounds"]:
                if inbound["type"] == "vless":
                    inbound["users"] = [u for u in inbound["users"] if u["uuid"] != peer["uuid"]]
                elif inbound["type"] == "hysteria2":
                    inbound["users"] = [
                        u for u in inbound["users"] if u["password"] != peer["password"]
                    ]
                elif inbound["type"] == "tuic":
                    inbound["users"] = [u for u in inbound["users"] if u["uuid"] != peer["uuid"]]
                elif inbound["type"] == "wireguard":
                    inbound["peers"] = [
                        p for p in inbound["peers"] if p["public_key"] != peer["wg_public_key"]
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

        configs = []

        # VLESS Reality
        reality_pub = settings.reality_public_key or ""
        short_id = settings.reality_short_id or ""
        sni = settings.reality_dest.split(":")[0]
        vless_link = f"vless://{peer['uuid']}@{ip}:{self.reality_port}?encryption=none&flow=xtls-rprx-vision&security=reality&sni={sni}&fp=chrome&pbk={reality_pub}&sid={short_id}&type=tcp&headerType=none#Kosatka-VLESS-{client_id}"
        configs.append(vless_link)

        # Hysteria2
        hysteria_link = f"hysteria2://{peer['password']}@{ip}:{self.hysteria_port}/?insecure=1&sni=google.com#Kosatka-Hysteria2-{client_id}"
        configs.append(hysteria_link)

        # TUIC
        tuic_link = f"tuic://{peer['uuid']}:{peer['password']}@{ip}:{self.tuic_port}/?congestion_control=bbr&alpn=h3&sni=google.com&udp_relay_mode=quic&allow_insecure=1#Kosatka-TUIC-{client_id}"
        configs.append(tuic_link)

        # WireGuard
        wg_server_pub = ""
        if SINGBOX_WG_KEY_PATH.exists():
            try:
                proc = await asyncio.create_subprocess_exec(
                    "sing-box",
                    "generate",
                    "wg-key",
                    "-p",
                    SINGBOX_WG_KEY_PATH.read_text().strip(),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await proc.communicate()
                if proc.returncode == 0:
                    wg_server_pub = stdout.decode().strip()
            except Exception:
                pass

        wg_config = f"""
[Interface]
PrivateKey = {peer['wg_private_key']}
Address = {peer['wg_ip']}/32
DNS = 1.1.1.1

[Peer]
PublicKey = {wg_server_pub}
Endpoint = {ip}:{self.wg_port}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 20
"""
        configs.append("--- WireGuard Config ---")
        configs.append(wg_config.strip())

        return "\n\n".join(configs)

    async def get_client_stats(self, client_id: str) -> Dict[str, Any]:
        return {"id": client_id, "uplink": 0, "downlink": 0}


# Legacy providers for backward compatibility if needed, but they should now use SingboxProvider
class Hysteria2Provider(SingboxProvider):
    def __init__(self, port: int = 443):
        super().__init__()
        self.hysteria_port = port


class TUICProvider(SingboxProvider):
    def __init__(self, port: int = 8443):
        super().__init__()
        self.tuic_port = port
