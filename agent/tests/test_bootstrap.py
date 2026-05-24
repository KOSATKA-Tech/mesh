from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from kosatka_agent import bootstrap


@pytest.mark.asyncio
async def test_get_public_ip():
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, text="8.8.8.8")
        ip = await bootstrap.get_public_ip()
        assert ip == "8.8.8.8"


@pytest.mark.asyncio
async def test_ensure_apt_packages():
    with (
        patch("shutil.which", return_value="/usr/bin/apt-get"),
        patch("kosatka_agent.bootstrap.run_command", AsyncMock()) as mock_run,
    ):
        await bootstrap.ensure_apt_packages(["curl"])
        assert mock_run.call_count == 2
        mock_run.assert_any_call(["apt-get", "install", "-y", "curl"])


@pytest.mark.asyncio
async def test_install_wireguard():
    with (
        patch("shutil.which", side_effect=[None, "/usr/bin/wg"]),
        patch("kosatka_agent.bootstrap.ensure_apt_packages", AsyncMock()) as mock_apt,
    ):
        await bootstrap.install_wireguard()
        assert mock_apt.called


@pytest.mark.asyncio
async def test_install_amneziawg():
    with (
        patch("shutil.which", return_value=None),
        patch("kosatka_agent.bootstrap.ensure_apt_packages", AsyncMock()),
        patch("kosatka_agent.bootstrap.run_command", AsyncMock()),
        patch(
            "httpx.AsyncClient.get",
            AsyncMock(return_value=MagicMock(status_code=200, content=b"bin")),
        ),
        patch("os.chmod"),
        patch("os.path.exists", return_value=False),
        patch("builtins.open", MagicMock()),
    ):
        await bootstrap.install_amneziawg()


@pytest.mark.asyncio
async def test_install_marzban():
    with (
        patch("shutil.which", side_effect=[None, None]),
        patch("kosatka_agent.bootstrap.run_command", AsyncMock(return_value="version")),
        patch(
            "httpx.AsyncClient.get",
            AsyncMock(return_value=MagicMock(status_code=200, content=b"script")),
        ),
        patch("builtins.open", MagicMock()),
    ):
        await bootstrap.install_marzban()


@pytest.mark.asyncio
async def test_install_marzban_plugin():
    with (
        patch("shutil.which") as mock_which,
        patch("kosatka_agent.bootstrap.run_command") as mock_run,
    ):
        # 1. docker exists (True)
        # 2. docker-compose binary missing (None)
        # 3. apt-get exists (True)
        mock_which.side_effect = [True, None, True]

        # 1. docker compose version fails
        # 2. apt-get update
        # 3. apt-get install
        mock_run.side_effect = [RuntimeError("no v2"), "updated", "installed"]

        await bootstrap.install_marzban()
        mock_run.assert_any_call(["apt-get", "install", "-y", "docker-compose-plugin"])


@pytest.mark.asyncio
async def test_bootstrap_provider_all():
    providers = {"wireguard": "wireguard", "awg": "amneziawg", "xray": "xray", "marzban": "marzban"}
    for p, func in providers.items():
        with patch(f"kosatka_agent.bootstrap.install_{func}", AsyncMock()) as mock_install:
            await bootstrap.bootstrap_provider(p)
            assert mock_install.called
