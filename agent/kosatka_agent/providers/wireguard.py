"""Vanilla WireGuard provider. Same semantics as AmneziaWGProvider but
without AmneziaWG's obfuscation parameters and against `wg`/`wg-quick`."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List

from ..config import settings
from . import _wgcore as wg
from .base import BaseAgentProvider

logger = logging.getLogger(__name__)

CMD = "wg"


class WireGuardProvider(BaseAgentProvider):
    def __init__(self, config_path: str | None = None) -> None:
        self.config_path = config_path or settings.wg_config_path
        self.interface = settings.wg_interface
        self.state_path = settings.wg_state_path
        # Written by roles/wireguard (NOT roles/awg). Vanilla-WG nodes never
        # run the awg role so falling back to awg_server_info_path would
        # produce a permanent RuntimeError.
        self.server_info_path = settings.wg_server_info_path
        self.lock = asyncio.Lock()

    def _server(self) -> wg.ServerInfo:
        server = wg.load_server_info(self.server_info_path)
        if server is None:
            raise RuntimeError(
                f"WG server info missing at {self.server_info_path}; "
                "provision a server key pair and write server info first."
            )
        return server

    async def get_clients(self) -> List[Dict[str, Any]]:
        state = wg.load_state(self.state_path)
        return [
            {"client_id": p.client_id, "address": p.address, "public_key": p.public_key}
            for p in state.peers.values()
        ]

    async def get_client(self, client_id: str) -> Dict[str, Any] | None:
        state = wg.load_state(self.state_path)
        peer = state.peers.get(client_id)
        if peer is None:
            return None
        return {"client_id": peer.client_id, "address": peer.address, "public_key": peer.public_key}

    async def create_client(self, client_data: Dict[str, Any]) -> Dict[str, Any]:
        async with self.lock:
            state = wg.load_state(self.state_path)
            raw_id = (
                client_data.get("external_id") or client_data.get("id") or client_data.get("name")
            )
            if not raw_id:
                raise ValueError("create_client: missing external_id/id/name")
            client_id = str(raw_id)

            if client_id in state.peers:
                peer = state.peers[client_id]
            else:
                server = self._server()
                private_key, public_key = await wg.generate_keypair(CMD)
                preshared_key = await wg.generate_preshared_key(CMD)
                address = wg.next_free_address(server.subnet, state)
                peer = wg.Peer(
                    client_id=client_id,
                    private_key=private_key,
                    public_key=public_key,
                    preshared_key=preshared_key,
                    address=address,
                )
                state.peers[client_id] = peer
                await wg.apply_peer(CMD, self.interface, peer)
                await wg.save_running_config(CMD, self.interface)
                wg.save_state(self.state_path, state)

            config_text = wg.render_client_config(peer, self._server())
            return {
                "id": peer.client_id,
                "client_id": peer.client_id,
                "external_id": peer.client_id,
                "public_key": peer.public_key,
                "address": peer.address,
                "config_text": config_text,
                "status": "added",
            }

    async def delete_client(self, client_id: str) -> bool:
        async with self.lock:
            state = wg.load_state(self.state_path)
            peer = state.peers.pop(str(client_id), None)
            if peer is None:
                return False
            try:
                await wg.remove_peer(CMD, self.interface, peer.public_key)
            except RuntimeError as exc:
                logger.warning("wg remove peer failed for %s: %s", client_id, exc)
            await wg.save_running_config(CMD, self.interface)
            wg.save_state(self.state_path, state)
            return True

    async def get_client_config(self, client_id: str) -> str:
        state = wg.load_state(self.state_path)
        peer = state.peers.get(str(client_id))
        if peer is None:
            return ""
        return wg.render_client_config(peer, self._server())

    async def get_client_stats(self, client_id: str) -> Dict[str, Any]:
        state = wg.load_state(self.state_path)
        peer = state.peers.get(str(client_id))
        if peer is None:
            return {"transfer_rx": 0, "transfer_tx": 0}
        try:
            dump = await wg.run([CMD, "show", self.interface, "dump"])
        except RuntimeError:
            return {"transfer_rx": 0, "transfer_tx": 0}
        for stats in wg.parse_wg_dump(dump):
            if stats.public_key == peer.public_key:
                # ``endpoint_ip`` powers the master's GeoIP-on-handshake
                # job in Phase 1b — strip the ``:port`` suffix so the
                # master service doesn't need to know the wire format.
                return {
                    "transfer_rx": stats.transfer_rx,
                    "transfer_tx": stats.transfer_tx,
                    "latest_handshake": stats.latest_handshake,
                    "endpoint_ip": stats.endpoint_ip,
                }
        return {"transfer_rx": 0, "transfer_tx": 0}
