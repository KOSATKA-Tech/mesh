from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from kosatka_agent.installer import SmartProvisioner


@pytest.mark.asyncio
async def test_is_inside_docker_env_file():
    with patch("os.path.exists") as mock_exists:
        mock_exists.side_effect = lambda p: p == "/.dockerenv"
        provisioner = SmartProvisioner()
        assert provisioner.is_inside_docker() is True


@pytest.mark.asyncio
async def test_is_inside_docker_cgroup():
    with patch("os.path.exists") as mock_exists:
        mock_exists.side_effect = lambda p: False
        with patch(
            "builtins.open",
            MagicMock(
                return_value=MagicMock(
                    __enter__=MagicMock(
                        return_value=MagicMock(
                            read=MagicMock(return_value="1:name=systemd:/docker/1234")
                        )
                    )
                )
            ),
        ):
            provisioner = SmartProvisioner()
            assert provisioner.is_inside_docker() is True


@pytest.mark.asyncio
async def test_get_system_info():
    with (
        patch("platform.machine", return_value="x86_64"),
        patch("platform.system", return_value="Linux"),
    ):
        provisioner = SmartProvisioner()
        info = provisioner.get_system_info()
        assert info["arch"] == "amd64"
        assert info["os"] == "linux"

    with (
        patch("platform.machine", return_value="aarch64"),
        patch("platform.system", return_value="Linux"),
    ):
        provisioner = SmartProvisioner()
        info = provisioner.get_system_info()
        assert info["arch"] == "arm64"


@pytest.mark.asyncio
async def test_get_binary_url_xray():
    with patch(
        "kosatka_agent.installer.SmartProvisioner.get_system_info",
        return_value={"arch": "amd64", "os": "linux"},
    ):
        provisioner = SmartProvisioner()
        url = provisioner._get_binary_url("xray")
        assert "Xray-linux-64.zip" in url

    with patch(
        "kosatka_agent.installer.SmartProvisioner.get_system_info",
        return_value={"arch": "arm64", "os": "linux"},
    ):
        provisioner = SmartProvisioner()
        url = provisioner._get_binary_url("xray")
        assert "Xray-linux-arm64-v8a.zip" in url


@pytest.mark.asyncio
async def test_download_and_extract_zip(tmp_path):
    bin_dir = tmp_path / "bin"
    provisioner = SmartProvisioner(bin_path=str(bin_dir))

    # Create a dummy zip file
    import io
    import zipfile

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        zip_file.writestr("xray", b"dummy xray binary")

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.content = zip_buffer.getvalue()
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        await provisioner._download_and_extract("https://example.com/xray.zip", "xray")

    assert (bin_dir / "xray").exists()
    assert (bin_dir / "xray").read_text() == "dummy xray binary"


@pytest.mark.asyncio
async def test_ensure_providers_orchestration():
    provisioner = SmartProvisioner()
    with (
        patch.object(provisioner, "_get_binary_url", return_value="https://example.com/bin"),
        patch.object(provisioner, "_download_and_extract", new_callable=AsyncMock) as mock_download,
        patch("shutil.which", return_value=None),
        patch("os.path.exists", return_value=False),
    ):

        await provisioner.ensure_providers()

        assert mock_download.call_count == 2
        mock_download.assert_any_call("https://example.com/bin", "xray")
        mock_download.assert_any_call("https://example.com/bin", "wireguard-go")
