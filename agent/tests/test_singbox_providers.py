import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from kosatka_agent.providers.singbox import SingboxProvider


@pytest.fixture
def mock_bootstrap():
    with patch("kosatka_agent.providers.singbox.bootstrap_provider", new_callable=AsyncMock) as m:
        yield m


@pytest.fixture
def mock_run_command():
    with patch("kosatka_agent.providers.singbox.run_command", new_callable=AsyncMock) as m:
        yield m


@pytest.fixture
def mock_public_ip():
    with patch("kosatka_agent.providers.singbox.get_public_ip", new_callable=AsyncMock) as m:
        m.return_value = "1.2.3.4"
        yield m


@pytest.fixture
def mock_subprocess():
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as m:
        process = MagicMock()
        process.returncode = 0
        process.communicate = AsyncMock(return_value=(b"mock-key", b""))
        process.wait = AsyncMock(return_value=0)
        m.return_value = process
        yield m


@pytest.mark.asyncio
async def test_unified_singbox_provider(
    mock_bootstrap, mock_run_command, mock_public_ip, mock_subprocess, tmp_path
):
    # Setup paths to use tmp_path
    with (
        patch("kosatka_agent.providers.singbox.SINGBOX_CONFIG_DIR", tmp_path / "etc/sing-box"),
        patch("kosatka_agent.providers.singbox.SINGBOX_STATE_DIR", tmp_path / "opt/kosatka/agent"),
        patch(
            "kosatka_agent.providers.singbox.SINGBOX_CERT_PATH", tmp_path / "etc/sing-box/cert.pem"
        ),
        patch(
            "kosatka_agent.providers.singbox.SINGBOX_KEY_PATH", tmp_path / "etc/sing-box/key.pem"
        ),
        patch(
            "kosatka_agent.providers.singbox.SINGBOX_WG_KEY_PATH",
            tmp_path / "etc/sing-box/wg_private.key",
        ),
    ):

        provider = SingboxProvider()

        # Ensure directories exist for the mock to work
        (tmp_path / "etc/sing-box").mkdir(parents=True)
        (tmp_path / "opt/kosatka/agent").mkdir(parents=True)
        # Mock certs existence
        (tmp_path / "etc/sing-box/cert.pem").write_text("cert")
        (tmp_path / "etc/sing-box/key.pem").write_text("key")
        (tmp_path / "etc/sing-box/wg_private.key").write_text("server-wg-priv")

        client_data = {
            "id": "test-unified",
            "password": "unified-password",
            "wg_public_key": "client-wg-pub",
            "wg_private_key": "client-wg-priv",
        }
        peer = await provider.create_client(client_data)

        assert peer["id"] == "test-unified"
        assert peer["password"] == "unified-password"
        assert peer["wg_ip"] == "10.10.10.2"

        # Check config generation
        config = json.loads(provider.config_path.read_text())

        # Should have 4 inbounds
        inbound_types = [ib["type"] for ib in config["inbounds"]]
        assert "vless" in inbound_types
        assert "hysteria2" in inbound_types
        assert "tuic" in inbound_types
        assert "wireguard" in inbound_types

        # Check VLESS user
        vless_inbound = next(ib for ib in config["inbounds"] if ib["type"] == "vless")
        assert vless_inbound["users"][0]["uuid"] == peer["uuid"]

        # Check Hysteria2 user
        hysteria_inbound = next(ib for ib in config["inbounds"] if ib["type"] == "hysteria2")
        assert hysteria_inbound["users"][0]["password"] == "unified-password"

        # Check TUIC user
        tuic_inbound = next(ib for ib in config["inbounds"] if ib["type"] == "tuic")
        assert tuic_inbound["users"][0]["uuid"] == peer["uuid"]
        assert tuic_inbound["users"][0]["password"] == "unified-password"

        # Check WG peer
        wg_inbound = next(ib for ib in config["inbounds"] if ib["type"] == "wireguard")
        assert wg_inbound["peers"][0]["public_key"] == "client-wg-pub"
        assert wg_inbound["peers"][0]["allowed_ips"] == ["10.10.10.2/32"]

        # Check client config
        configs = await provider.get_client_config("test-unified")
        assert "vless://" in configs
        assert "hysteria2://" in configs
        assert "tuic://" in configs
        assert "PrivateKey = client-wg-priv" in configs
        assert "Address = 10.10.10.2/32" in configs
