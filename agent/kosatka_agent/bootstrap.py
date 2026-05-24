import asyncio
import logging
import os
import shutil

import httpx

logger = logging.getLogger(__name__)


async def run_command(cmd: list[str], check: bool = True) -> str:
    """Run a shell command and return its output."""
    logger.info(f"Executing: {' '.join(cmd)}")
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if check and proc.returncode != 0:
        error_msg = stderr.decode().strip()
        logger.error(f"Command failed with rc={proc.returncode}: {error_msg}")
        raise RuntimeError(f"Command {' '.join(cmd)} failed: {error_msg}")
    return stdout.decode().strip()


async def get_public_ip() -> str:
    """Fetch the public IP of the current host."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("https://api.ipify.org")
            resp.raise_for_status()
            return resp.text.strip()
    except Exception as exc:
        logger.error(f"Failed to fetch public IP: {exc}")
        # Fallback to a common interface IP if possible, but public IP is preferred
        return "127.0.0.1"


async def ensure_apt_packages(packages: list[str]):
    """Ensure specified apt packages are installed."""
    if shutil.which("apt-get"):
        await run_command(["apt-get", "update"])
        await run_command(["apt-get", "install", "-y"] + packages)
    else:
        logger.warning("apt-get not found, skipping package installation")


async def install_wireguard():
    """Install WireGuard tools."""
    if not shutil.which("wg"):
        logger.info("WireGuard tools missing, installing...")
        # Install 'wireguard' package which includes tools and kernel module
        await ensure_apt_packages(["wireguard", "wireguard-tools", "iproute2", "iptables"])


async def install_amneziawg():
    """Install AmneziaWG tools."""
    if not shutil.which("awg"):
        logger.info("AmneziaWG tools missing, installing via PPA...")
        await ensure_apt_packages(["software-properties-common"])
        await run_command(["add-apt-repository", "-y", "ppa:amnezia/ppa"])
        await ensure_apt_packages(["amneziawg-tools"])

        # Also try to get amneziawg-go if kernel module might be missing
        if not os.path.exists("/usr/local/bin/amneziawg-go"):
            logger.info("Downloading amneziawg-go...")
            url = "https://github.com/amnezia-vpn/amneziawg-go/releases/latest/download/amneziawg-go-linux-amd64"
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, follow_redirects=True)
                resp.raise_for_status()
                with open("/usr/local/bin/amneziawg-go", "wb") as f:
                    f.write(resp.content)
            os.chmod("/usr/local/bin/amneziawg-go", 0o755)


async def install_xray():
    """Install Xray core."""
    if not shutil.which("xray"):
        logger.info("Xray core missing, installing...")
        url = "https://github.com/XTLS/Xray-install/raw/main/install-release.sh"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, follow_redirects=True)
            resp.raise_for_status()
            with open("/tmp/install-xray.sh", "wb") as f:
                f.write(resp.content)
        os.chmod("/tmp/install-xray.sh", 0o755)
        await run_command(["bash", "/tmp/install-xray.sh"])


async def install_marzban():
    """Ensure Marzban requirements (Docker)."""
    if not shutil.which("docker"):
        logger.info("Docker missing, attempting to install...")
        await run_command(["curl", "-fsSL", "https://get.docker.com", "-o", "get-docker.sh"])
        await run_command(["sh", "get-docker.sh"])

    # Check for docker compose (plugin or binary)
    try:
        await run_command(["docker", "compose", "version"])
    except Exception:
        if not shutil.which("docker-compose"):
            logger.info("Docker Compose missing, installing...")
            await ensure_apt_packages(["docker-compose-plugin"])


async def bootstrap_provider(provider_type: str):
    """Bootstrap the specified provider."""
    if provider_type == "wireguard":
        await install_wireguard()
    elif provider_type == "awg":
        await install_amneziawg()
    elif provider_type == "xray":
        await install_xray()
    elif provider_type == "marzban":
        await install_marzban()
