"""Shared primitives for AmneziaWG / WireGuard providers.

The agent runs with `network_mode: host` + `NET_ADMIN` so it can exec
`awg`/`wg` directly against the host's kernel interface and persist config
to the host's `/etc/amnezia/amneziawg/wg0.conf` or `/etc/wireguard/wg0.conf`
via a bind-mount.

Peer state is kept in a side-car JSON file (`awg_peers.json` /
`wg_peers.json`) so the agent can rebuild the running set after a reboot
without parsing the underlying conf file, and so `get_client_config` can
answer without needing the client's private key from the wire format.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


# Keys of AmneziaWG obfuscation parameters we forward to clients. These must
# match the values set in the server's wg0.conf [Interface] block or the
# handshake will silently fail.
AWG_PARAM_KEYS = ("Jc", "Jmin", "Jmax", "S1", "S2", "H1", "H2", "H3", "H4")


@dataclass
class ServerInfo:
    public_key: str
    endpoint: str
    subnet: str = "10.8.0.0/24"
    dns: str = "1.1.1.1, 1.0.0.1"
    # AmneziaWG obfuscation params; empty for vanilla WireGuard.
    awg_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Peer:
    client_id: str
    private_key: str
    public_key: str
    preshared_key: str
    address: str  # e.g. 10.8.0.5/32


@dataclass
class PeerState:
    peers: Dict[str, Peer] = field(default_factory=dict)


async def run(cmd: List[str], stdin_text: str | None = None) -> str:
    """Run a subprocess; return stdout on success, raise on failure."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE if stdin_text is not None else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_b, stderr_b = await proc.communicate(input=stdin_text.encode() if stdin_text else None)
    stdout = stdout_b.decode().strip()
    stderr = stderr_b.decode().strip()
    if proc.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)!r} failed: rc={proc.returncode} stderr={stderr}")
    return stdout


def load_server_info(path: str) -> ServerInfo | None:
    try:
        data = json.loads(Path(path).read_text())
    except FileNotFoundError:
        logger.warning("Server info file %s not found; provider is not yet bootstrapped", path)
        return None
    except json.JSONDecodeError as exc:
        logger.error("Malformed server info file %s: %s", path, exc)
        return None
    # Peel off the AmneziaWG obfuscation params from the top-level JSON object
    # (ansible's awg role writes them flat alongside public_key/endpoint/...).
    awg_params: Dict[str, Any] = {}
    for key in AWG_PARAM_KEYS:
        if key in data:
            awg_params[key] = data.pop(key)
    # Allow either flat keys or an explicit `awg_params` object.
    awg_params.update(data.pop("awg_params", {}) or {})
    try:
        return ServerInfo(awg_params=awg_params, **data)
    except TypeError as exc:
        logger.error("Server info %s has unexpected fields: %s", path, exc)
        return None


def load_state(path: str) -> PeerState:
    try:
        raw = json.loads(Path(path).read_text())
        return PeerState(peers={k: Peer(**v) for k, v in raw.get("peers", {}).items()})
    except FileNotFoundError:
        return PeerState()
    except (json.JSONDecodeError, TypeError) as exc:
        logger.warning("Malformed state file %s: %s (starting fresh)", path, exc)
        return PeerState()


def save_state(path: str, state: PeerState) -> None:
    # The state file contains every peer's private_key + preshared_key, so we
    # open the temp file with an explicit 0o600 mode (umask-independent) before
    # the atomic rename. Without this, default umask would leave it world-
    # readable — a serious issue since the file is bind-mounted to the host.
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    payload = {"peers": {k: asdict(v) for k, v in state.peers.items()}}
    tmp = Path(path).with_suffix(".tmp")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, json.dumps(payload, indent=2).encode())
    finally:
        os.close(fd)
    os.replace(tmp, path)


def next_free_address(subnet: str, state: PeerState) -> str:
    """Return the next free host IP in `subnet` (server is .1 by convention)."""
    net = ipaddress.ip_network(subnet, strict=False)
    used: set[str] = {str(net.network_address + 1)}  # reserve .1 for server
    for peer in state.peers.values():
        # address is "10.8.0.5/32"
        used.add(peer.address.split("/", 1)[0])
    for host in net.hosts():
        ip = str(host)
        if ip not in used:
            return f"{ip}/32"
    raise RuntimeError(f"No free addresses in subnet {subnet}")


async def generate_keypair(cmd_prefix: str) -> tuple[str, str]:
    """Return (private_key, public_key) using wg/awg toolchain."""
    privkey = await run([cmd_prefix, "genkey"])
    pubkey = await run([cmd_prefix, "pubkey"], stdin_text=privkey)
    return privkey, pubkey


async def generate_preshared_key(cmd_prefix: str) -> str:
    return await run([cmd_prefix, "genpsk"])


def render_client_config(
    peer: Peer,
    server: ServerInfo,
    awg_params: Dict[str, Any] | None = None,
) -> str:
    """Render a [Interface]+[Peer] config for the client."""
    lines = [
        "[Interface]",
        f"PrivateKey = {peer.private_key}",
        f"Address = {peer.address}",
        f"DNS = {server.dns}",
    ]
    if awg_params:
        for key in ("Jc", "Jmin", "Jmax", "S1", "S2", "H1", "H2", "H3", "H4"):
            if key in awg_params:
                lines.append(f"{key} = {awg_params[key]}")
    lines.extend(
        [
            "",
            "[Peer]",
            f"PublicKey = {server.public_key}",
            f"PresharedKey = {peer.preshared_key}",
            f"Endpoint = {server.endpoint}",
            "AllowedIPs = 0.0.0.0/0, ::/0",
            "PersistentKeepalive = 25",
        ]
    )
    return "\n".join(lines) + "\n"


async def bootstrap_server(
    cmd_prefix: str,
    server_info_path: str,
    interface: str,
    subnet: str = "10.8.0.0/24",
    port: int = 51820,
) -> ServerInfo:
    """Fully bootstrap a WG/AWG server: install, gen keys, get IP, write conf, start."""
    from ..bootstrap import bootstrap_provider, get_public_ip

    # 1. Ensure tools are installed
    await bootstrap_provider(cmd_prefix)

    # 2. Generate keys
    privkey, pubkey = await generate_keypair(cmd_prefix)

    # 3. Get public IP
    ip = await get_public_ip()
    endpoint = f"{ip}:{port}"

    # 4. AmneziaWG specific obfuscation
    awg_params = {}
    if cmd_prefix == "awg":
        awg_params = {
            "Jc": 4,
            "Jmin": 40,
            "Jmax": 70,
            "S1": 15,
            "S2": 24,
            "H1": 1,
            "H2": 2,
            "H3": 3,
            "H4": 4,
        }

    server = ServerInfo(public_key=pubkey, endpoint=endpoint, subnet=subnet, awg_params=awg_params)

    # 5. Save server info
    save_server_info(server_info_path, server)

    # 6. Generate and save wg0.conf
    # We write a minimal config. wg-quick will use this.
    conf_dir = "/etc/amnezia/amneziawg" if cmd_prefix == "awg" else "/etc/wireguard"
    os.makedirs(conf_dir, exist_ok=True)
    conf_path = Path(conf_dir) / f"{interface}.conf"

    conf_lines = [
        "[Interface]",
        f"PrivateKey = {privkey}",
        f"Address = {ipaddress.ip_network(subnet)[1]}/24",
        f"ListenPort = {port}",
    ]
    for k, v in awg_params.items():
        conf_lines.append(f"{k} = {v}")

    conf_path.write_text("\n".join(conf_lines) + "\n")

    # 7. Bring up the interface
    try:
        await run([f"{cmd_prefix}-quick", "up", interface])
    except RuntimeError as exc:
        if "already exists" in str(exc):
            logger.info(f"Interface {interface} already up")
        else:
            raise

    return server


def save_server_info(path: str, server: ServerInfo) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    data = asdict(server)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


async def apply_peer(cmd_prefix: str, interface: str, peer: Peer) -> None:
    await run(
        [
            cmd_prefix,
            "set",
            interface,
            "peer",
            peer.public_key,
            "preshared-key",
            "/dev/stdin",
            "allowed-ips",
            peer.address,
        ],
        stdin_text=peer.preshared_key + "\n",
    )


async def remove_peer(cmd_prefix: str, interface: str, public_key: str) -> None:
    await run([cmd_prefix, "set", interface, "peer", public_key, "remove"])


async def save_running_config(cmd_prefix: str, interface: str) -> None:
    """Best-effort: persist the running interface to disk. Missing binary
    (e.g. on hosts without `wg-quick`) is not fatal — the state file is
    still authoritative."""
    try:
        await run([f"{cmd_prefix}-quick", "save", interface])
    except (FileNotFoundError, RuntimeError) as exc:
        logger.debug("%s-quick save failed (ignored): %s", cmd_prefix, exc)
