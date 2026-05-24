import json
from unittest.mock import AsyncMock, patch

import pytest
import respx
from httpx import Response
from kosatka_agent.providers import _wgcore
from kosatka_agent.providers.marzban import MarzbanProvider
from kosatka_agent.providers.wireguard import WireGuardProvider
from kosatka_agent.providers.xray import XrayProvider


@pytest.mark.asyncio
async def test_marzban_provider_full():
    url = "http://marzban:8000"
    username = "admin"
    password = "password"
    provider = MarzbanProvider(url, username, password)

    with respx.mock:
        # Mock token
        respx.post(f"{url}/api/admin/token").mock(
            return_value=Response(200, json={"access_token": "test-token"})
        )

        # Mock users list
        respx.get(f"{url}/api/users").mock(
            return_value=Response(200, json={"users": [{"username": "user1", "status": "active"}]})
        )

        # Mock single user
        respx.get(f"{url}/api/user/user1").mock(
            return_value=Response(
                200,
                json={"username": "user1", "status": "active", "subscription_url": "http://sub"},
            )
        )

        # Mock user creation
        respx.post(f"{url}/api/user").mock(
            return_value=Response(
                200, json={"username": "newuser", "subscription_url": "http://newsub"}
            )
        )

        # Mock deletion
        respx.delete(f"{url}/api/user/user1").mock(return_value=Response(200))

        assert await provider._get_token() == "test-token"

        clients = await provider.get_clients()
        assert len(clients) == 1
        assert clients[0]["client_id"] == "user1"

        client = await provider.get_client("user1")
        assert client["client_id"] == "user1"

        new_client = await provider.create_client({"external_id": "newuser"})
        assert new_client["id"] == "newuser"

        assert await provider.delete_client("user1") is True
        assert await provider.get_client_config("user1") == "http://sub"

        # Test stats
        respx.get(f"{url}/api/user/user1").mock(
            return_value=Response(200, json={"used_traffic": 1000})
        )
        stats = await provider.get_client_stats("user1")
        assert stats["used_traffic"] == 1000


@pytest.mark.asyncio
async def test_xray_provider(tmp_path, monkeypatch):
    # Mock Xray paths
    monkeypatch.setattr("kosatka_agent.providers.xray.XRAY_CONFIG_DIR", tmp_path / "etc/xray")
    monkeypatch.setattr(
        "kosatka_agent.providers.xray.XRAY_CONFIG_PATH", tmp_path / "etc/xray/config.json"
    )
    monkeypatch.setattr(
        "kosatka_agent.providers.xray.XRAY_STATE_PATH",
        tmp_path / "opt/kosatka/agent/xray_peers.json",
    )

    provider = XrayProvider()

    # Mock bootstrap and IP
    with (
        patch("kosatka_agent.providers.xray.bootstrap_provider", AsyncMock()),
        patch("kosatka_agent.providers.xray.get_public_ip", AsyncMock(return_value="1.1.1.1")),
    ):

        # Test client creation
        res = await provider.create_client({"external_id": "client1"})
        assert res["id"] == "client1"
        assert "uuid" in res

        # Test state persistence
        assert (tmp_path / "opt/kosatka/agent/xray_peers.json").exists()

        # Test config generation
        config = json.loads((tmp_path / "etc/xray/config.json").read_text())
        assert len(config["inbounds"][0]["settings"]["clients"]) == 1

        # Test config retrieval
        link = await provider.get_client_config("client1")
        assert "vless://" in link
        assert "1.1.1.1" in link

        # Test deletion
        assert await provider.delete_client("client1") is True
        config_after = json.loads((tmp_path / "etc/xray/config.json").read_text())
        assert len(config_after["inbounds"][0]["settings"]["clients"]) == 0


@pytest.mark.asyncio
async def test_wireguard_provider(tmp_path):
    server_info = tmp_path / "awg_server.json"
    server_info.write_text(
        json.dumps(
            {
                "public_key": "server-pub",
                "endpoint": "node.example.com:51820",
                "subnet": "10.8.0.0/24",
                "dns": "1.1.1.1",
            }
        )
    )
    state_path = tmp_path / "wg_peers.json"

    provider = WireGuardProvider("/etc/wireguard/wg0.conf")
    provider.server_info_path = str(server_info)
    provider.state_path = str(state_path)

    async def fake_run(cmd, stdin_text=None):
        head = cmd[:2]
        if head == ["wg", "genkey"]:
            return "client-priv"
        if head == ["wg", "pubkey"]:
            return "client-pub"
        if head == ["wg", "genpsk"]:
            return "client-psk"
        if cmd[:3] == ["wg", "show", provider.interface]:
            return "client-pub\tpsk\tendpoint\t10.8.0.2/32\t0\t0\t0\t0"
        if cmd[:2] == ["ip", "link"]:
            return "up"
        return ""

    with patch.object(_wgcore, "run", AsyncMock(side_effect=fake_run)):
        assert await provider.get_clients() == []

        res = await provider.create_client({"external_id": "client1"})
        assert res["id"] == "client1"
        assert "[Interface]" in res["config_text"]

        assert await provider.delete_client("client1") is True
        assert await provider.get_client_config("client1") == ""

        # Test stats
        state_path.write_text(
            json.dumps(
                {
                    "peers": {
                        "client1": {
                            "client_id": "client1",
                            "private_key": "priv",
                            "public_key": "pub",
                            "preshared_key": "psk",
                            "address": "10.8.0.2/32",
                        }
                    }
                }
            )
        )
        stats = await provider.get_client_stats("client1")
        assert stats["transfer_rx"] == 0
