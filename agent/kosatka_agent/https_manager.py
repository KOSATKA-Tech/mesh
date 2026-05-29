import logging
import os
import subprocess
import tempfile

logger = logging.getLogger("kosatka.https")


def start_https_proxy(domain: str, port: int):
    """
    Spawns a Caddy process to handle automatic HTTPS for the given domain.
    Proxies traffic to the local port.
    """
    if not domain:
        logger.error("HTTPS proxy requested but no domain provided.")
        return

    caddyfile_content = f"""
{domain} {{
    reverse_proxy localhost:{port}
}}
"""
    # Write to a temporary file
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
        tmp.write(caddyfile_content)
        tmp_path = tmp.name

    logger.info(f"Starting Caddy for {domain} -> localhost:{port}")
    try:
        # Run Caddy in the background
        subprocess.Popen(["caddy", "run", "--config", tmp_path, "--adapter", "caddyfile"])
    except FileNotFoundError:
        logger.error("Caddy binary not found. Please install Caddy to use auto-HTTPS.")
    except Exception as e:
        logger.error(f"Failed to start Caddy: {e}")
