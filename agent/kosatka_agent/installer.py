import logging
import os
import platform
import shutil
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

        elif provider == "wireguard-go":
            # Since official WireGuard/wireguard-go doesn't provide binaries,
            # we'll use a known reliable source or a placeholder.
            # For this task, we'll use amneziawg-go as a reference or a hypothetical mirror.
            # Using amneziawg-go releases as they ARE available and used in bootstrap.py
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
        """Download a file and extract if it's a zip, then move to bin_path."""
        os.makedirs(self.bin_path, exist_ok=True)
        temp_file = os.path.join("/tmp", os.path.basename(url))

        logger.info(f"Downloading {url} to {temp_file}")
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            with open(temp_file, "wb") as f:
                f.write(resp.content)

        if temp_file.endswith(".zip"):
            extract_path = os.path.join("/tmp", f"extracted_{target_name}")
            os.makedirs(extract_path, exist_ok=True)
            with zipfile.ZipFile(temp_file, "r") as zip_ref:
                zip_ref.extractall(extract_path)

            # Find the actual binary in the extracted files
            source_bin = os.path.join(extract_path, target_name)
            if not os.path.exists(source_bin):
                # Fallback: find any executable or the first file if target_name not found
                files = os.listdir(extract_path)
                if files:
                    source_bin = os.path.join(extract_path, files[0])

            shutil.move(source_bin, os.path.join(self.bin_path, target_name))
            shutil.rmtree(extract_path)
        else:
            shutil.move(temp_file, os.path.join(self.bin_path, target_name))

        if os.path.exists(temp_file):
            os.remove(temp_file)

        bin_full_path = os.path.join(self.bin_path, target_name)
        os.chmod(bin_full_path, 0o755)
        logger.info(f"Successfully installed {target_name} to {bin_full_path}")

    async def ensure_providers(self):
        """Orchestrate detection and download of providers."""
        logger.info(f"Ensuring providers for {self.os_info}")

        # For now, we'll ensure xray if not present
        if not shutil.which("xray") and not os.path.exists(os.path.join(self.bin_path, "xray")):
            try:
                url = self._get_binary_url("xray")
                await self._download_and_extract(url, "xray")
            except Exception as e:
                logger.error(f"Failed to provision xray: {e}")

        # Ensure wireguard-go if not present and kernel WG might be missing
        if not shutil.which("wg") and not os.path.exists(
            os.path.join(self.bin_path, "wireguard-go")
        ):
            try:
                url = self._get_binary_url("wireguard-go")
                await self._download_and_extract(url, "wireguard-go")
            except Exception as e:
                logger.error(f"Failed to provision wireguard-go: {e}")

        # Verify binaries
        for cmd in ["xray", "wireguard-go"]:
            full_path = os.path.join(self.bin_path, cmd)
            if os.path.exists(full_path):
                # We could run --version here, but some binaries might fail in certain envs (e.g. qemu)
                # For now, existence and chmod 755 is a good start.
                logger.info(f"Provider {cmd} is ready at {full_path}")
