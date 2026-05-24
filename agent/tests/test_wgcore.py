import json
import os
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

import pytest
from kosatka_agent.providers import _wgcore


@pytest.mark.asyncio
async def test_interface_exists():
    with patch("kosatka_agent.providers._wgcore.run", AsyncMock()) as mock_run:
        assert await _wgcore.interface_exists("wg0") is True
        mock_run.side_effect = RuntimeError("error")
        assert await _wgcore.interface_exists("wg0") is False


def test_load_save_server_info(tmp_path):
    path = tmp_path / "server.json"
    server = _wgcore.ServerInfo(public_key="pub", endpoint="1.1.1.1:51820")
    _wgcore.save_server_info(str(path), server)
    
    loaded = _wgcore.load_server_info(str(path))
    assert loaded.public_key == "pub"
    assert loaded.endpoint == "1.1.1.1:51820"


def test_load_save_state(tmp_path):
    path = tmp_path / "state.json"
    peer = _wgcore.Peer(client_id="1", private_key="priv", public_key="pub", preshared_key="psk", address="10.8.0.2/32")
    state = _wgcore.PeerState(peers={"1": peer})
    _wgcore.save_state(str(path), state)
    
    loaded = _wgcore.load_state(str(path))
    assert loaded.peers["1"].client_id == "1"


def test_next_free_address():
    state = _wgcore.PeerState()
    addr = _wgcore.next_free_address("10.8.0.0/24", state)
    assert addr == "10.8.0.2/32"
    
    state.peers["1"] = _wgcore.Peer(client_id="1", private_key="", public_key="", preshared_key="", address="10.8.0.2/32")
    addr2 = _wgcore.next_free_address("10.8.0.0/24", state)
    assert addr2 == "10.8.0.3/32"


@pytest.mark.asyncio
async def test_bootstrap_server(tmp_path):
    server_info_path = tmp_path / "wg_server.json"
    interface = "wg0"
    
    with patch("kosatka_agent.bootstrap.bootstrap_provider", AsyncMock()), \
         patch("kosatka_agent.providers._wgcore.generate_keypair", AsyncMock(return_value=("priv", "pub"))), \
         patch("kosatka_agent.bootstrap.get_public_ip", AsyncMock(return_value="1.1.1.1")), \
         patch("kosatka_agent.providers._wgcore.run", AsyncMock()), \
         patch("os.makedirs"), \
         patch("pathlib.Path.write_text"):
        
        server = await _wgcore.bootstrap_server("wg", str(server_info_path), interface)
        assert server.public_key == "pub"
        assert server.endpoint == "1.1.1.1:51820"
        assert server_info_path.exists()
