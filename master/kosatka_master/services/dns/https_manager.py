import logging
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
{{
    servers {{
        timeouts {{
            read_body 10s
            read_header 5s
            write 10s
            idle 30s
        }}
    }}
}}

{domain} {{
    # Protect Admin UI from public access
    # Only allow API and Subscription endpoints
    @disallowed path /admin* /
    handle @disallowed {{
        respond "Access Denied. Use SSH tunnel to access Admin UI." 403
    }}

    # Allow everything else (API, Subscriptions)
    handle {{
        reverse_proxy localhost:{port}
    }}
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
