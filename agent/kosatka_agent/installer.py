import logging
import os
import platform
import shutil
import tarfile
import zipfile

import httpx

logger = logging.getLogger(__name__)


class SmartProvisioner:
    def __init__(self, bin_path: str = "/opt/kosatka/bin/"):
        self.bin_path = bin_path
        self.os_info = self.get_system_info()

    def is_inside_docker(self) -> bool:
        """Check if we are running inside a Docker container."""
        if os.path.exists("/.dockerenv"):
            return True
        try:
            with open("/proc/1/cgroup", "rt") as f:
                if "docker" in f.read():
                    return True
        except Exception:
            pass
        return False

    def get_system_info(self) -> dict:
        """Identify architecture and OS."""
        machine = platform.machine().lower()
        system = platform.system().lower()

        # Normalize architecture
        if machine in ("x86_64", "amd64"):
            arch = "amd64"
        elif machine in ("aarch64", "arm64"):
            arch = "arm64"
        elif "arm" in machine:
            arch = "arm"
        else:
            arch = machine

        return {"arch": arch, "os": system}

    def _get_binary_url(self, provider: str) -> str:
        """Generate download URL for the provider binary."""
        arch = self.os_info["arch"]

        if provider == "xray":
            # XTLS/Xray-core naming: Xray-linux-64.zip, Xray-linux-arm64-v8a.zip
            if arch == "amd64":
                file_name = "Xray-linux-64.zip"
            elif arch == "arm64":
                file_name = "Xray-linux-arm64-v8a.zip"
            else:
                file_name = f"Xray-linux-{arch}.zip"
            return f"https://github.com/XTLS/Xray-core/releases/latest/download/{file_name}"

        elif provider == "sing-box":
            # sing-box-1.9.3-linux-amd64.tar.gz
            version = "1.9.3"
            file_name = f"sing-box-{version}-linux-{arch}.tar.gz"
            return f"https://github.com/SagerNet/sing-box/releases/download/v{version}/{file_name}"

        elif provider == "wireguard-go":
            if arch == "amd64":
                file_name = "amneziawg-go-linux-amd64"
            elif arch == "arm64":
                file_name = "amneziawg-go-linux-arm64"
            else:
                file_name = f"amneziawg-go-linux-{arch}"
            return (
                f"https://github.com/amnezia-vpn/amneziawg-go/releases/latest/download/{file_name}"
            )

        raise ValueError(f"Unknown provider: {provider}")

    async def _download_and_extract(self, url: str, target_name: str):
        """Download a file and extract if it's a zip or tar.gz, then move to bin_path."""
        os.makedirs(self.bin_path, exist_ok=True)
        temp_file = os.path.join("/tmp", os.path.basename(url))

        logger.info(f"Downloading {url} to {temp_file}")
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            with open(temp_file, "wb") as f:
                f.write(resp.content)

        extract_path = os.path.join("/tmp", f"extracted_{target_name}")
        os.makedirs(extract_path, exist_ok=True)

        if temp_file.endswith(".zip"):
            with zipfile.ZipFile(temp_file, "r") as zip_ref:
                zip_ref.extractall(extract_path)  # nosec
            self._move_binary(extract_path, target_name)
        elif temp_file.endswith(".tar.gz") or temp_file.endswith(".tgz"):
            with tarfile.open(temp_file, "r:gz") as tar_ref:
                tar_ref.extractall(extract_path)  # nosec
            self._move_binary(extract_path, target_name)
        else:
            shutil.move(temp_file, os.path.join(self.bin_path, target_name))

        if os.path.exists(temp_file):
            os.remove(temp_file)
        if os.path.exists(extract_path):
            shutil.rmtree(extract_path)

        bin_full_path = os.path.join(self.bin_path, target_name)
        os.chmod(bin_full_path, 0o755)
        logger.info(f"Successfully installed {target_name} to {bin_full_path}")

    def _move_binary(self, extract_path: str, target_name: str):
        """Find the binary in extract_path and move it to bin_path."""
        source_bin = None
        # Walk through extracted files to find the binary
        for root, _, files in os.walk(extract_path):
            if target_name in files:
                source_bin = os.path.join(root, target_name)
                break

        if not source_bin:
            # Fallback: find any file that matches target_name or just take the first file
            for root, _, files in os.walk(extract_path):
                for f in files:
                    if target_name in f:
                        source_bin = os.path.join(root, f)
                        break
                if source_bin:
                    break

        if source_bin:
            shutil.move(source_bin, os.path.join(self.bin_path, target_name))
        else:
            raise RuntimeError(f"Could not find {target_name} in extracted files")

    async def _ensure_binary(self, name: str, cmd: str | None = None):
        """Ensure a specific binary is installed."""
        check_cmd = cmd or name
        if not shutil.which(check_cmd) and not os.path.exists(os.path.join(self.bin_path, name)):
            try:
                url = self._get_binary_url(name)
                await self._download_and_extract(url, name)
            except Exception as e:
                logger.error(f"Failed to provision {name}: {e}")

    async def ensure_providers(self):
        """Orchestrate detection and download of providers."""
        logger.info(f"Ensuring providers for {self.os_info}")

        await self._ensure_binary("xray")
        await self._ensure_binary("sing-box")
        await self._ensure_binary("wireguard-go", "wg")

        # Verify binaries
        for cmd in ["xray", "sing-box", "wireguard-go"]:
            full_path = os.path.join(self.bin_path, cmd)
            if os.path.exists(full_path) or shutil.which(cmd):
                logger.info(f"Provider {cmd} is ready")
