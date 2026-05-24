import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from kosatka_agent.providers.singbox import Hysteria2Provider, TUICProvider


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
        process.communicate = AsyncMock(return_value=(b"", b""))
        m.return_value = process
        yield m


@pytest.mark.asyncio
async def test_hysteria2_provider_create_client(
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
    ):

        provider = Hysteria2Provider(port=443)

        # Ensure directories exist for the mock to work
        (tmp_path / "etc/sing-box").mkdir(parents=True)
        (tmp_path / "opt/kosatka/agent").mkdir(parents=True)
        # Mock certs existence to skip openssl call in _ensure_bootstrapped
        (tmp_path / "etc/sing-box/cert.pem").write_text("cert")
        (tmp_path / "etc/sing-box/key.pem").write_text("key")

        client_data = {"id": "test-user", "password": "test-password"}
        peer = await provider.create_client(client_data)

        assert peer["id"] == "test-user"
        assert peer["password"] == "test-password"

        # Check config generation
        config = json.loads(provider.config_path.read_text())
        assert config["inbounds"][0]["type"] == "hysteria2"
        assert config["inbounds"][0]["users"][0]["password"] == "test-password"

        # Check client config URL
        url = await provider.get_client_config("test-user")
        assert "hysteria2://test-password@1.2.3.4:443" in url


@pytest.mark.asyncio
async def test_tuic_provider_create_client(
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
    ):

        provider = TUICProvider(port=8443)

        # Ensure directories exist for the mock to work
        (tmp_path / "etc/sing-box").mkdir(parents=True)
        (tmp_path / "opt/kosatka/agent").mkdir(parents=True)
        # Mock certs existence
        (tmp_path / "etc/sing-box/cert.pem").write_text("cert")
        (tmp_path / "etc/sing-box/key.pem").write_text("key")

        client_data = {"id": "test-tuic-user", "password": "tuic-password"}
        peer = await provider.create_client(client_data)

        assert peer["id"] == "test-tuic-user"
        assert peer["password"] == "tuic-password"

        # Check config generation
        config = json.loads(provider.config_path.read_text())
        assert config["inbounds"][0]["type"] == "tuic"
        assert config["inbounds"][0]["users"][0]["uuid"] == peer["uuid"]
        assert config["inbounds"][0]["users"][0]["password"] == "tuic-password"

        # Check client config URL
        url = await provider.get_client_config("test-tuic-user")
        assert f"tuic://{peer['uuid']}:tuic-password@1.2.3.4:8443" in url
