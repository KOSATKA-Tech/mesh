import asyncio
import socket

import typer
from rich.console import Console

from . import config
from .api import APIClient

console = Console()


def get_public_ip():
    import httpx

    try:
        resp = httpx.get("https://api.ipify.org", timeout=5.0)
        return resp.text
    except Exception:
        # Fallback to local ip if offline or service down
        return socket.gethostbyname(socket.gethostname())


async def _join(master_url: str, api_key: str, role: str = "standalone", name: str | None = None):
    # 1. Gather info
    if not name:
        name = socket.gethostname()

    ip = get_public_ip()
    address = f"http://{ip}:8010"

    console.print(f"Joining mesh as [cyan]{name}[/cyan] at [green]{address}[/green]")

    # 2. Configure CLI temporarily to talk to master
    cfg = config.load_config()
    cfg.base_url = master_url
    cfg.api_key = api_key

    client = APIClient()
    client.config = cfg  # Inject temporary config

    # 3. Register with master
    assigned_domain = None
    try:
        payload = {"name": name, "address": address, "provider_type": "agent", "api_key": api_key}
        res = await client.request("POST", "/nodes/", json=payload)
        node_id = res.get("id")
        assigned_domain = res.get("assigned_domain")
        console.print(f"[green]✓ Registered with Master. Node ID: {node_id}[/green]")
        if assigned_domain:
            console.print(f"[green]✓ DNS assigned: {assigned_domain}[/green]")
    except Exception as e:
        console.print(f"[red]✗ Registration failed: {e}[/red]")
        return

    # 4. Generate local .env.agent
    env_content = f"""
AGENT_API_KEY={api_key}
AGENT_PROVIDER_TYPE=wireguard
AGENT_NODE_ROLE={role}
KOSATKA_MASTER_URL={master_url}
KOSATKA_API_KEY={api_key}
AGENT_DOMAIN={assigned_domain or ""}
AGENT_AUTO_HTTPS={'true' if assigned_domain else 'false'}
"""
    with open(".env.agent", "w") as f:
        f.write(env_content.strip())

    console.print("[green]✓ Generated .env.agent[/green]")
    console.print("\n[bold]Next steps:[/bold]")
    console.print("1. Run the agent: [cyan]kosatka-mesh agent run[/cyan]")
    console.print("2. Or use docker: [cyan]docker compose -f docker-compose.agent.yml up -d[/cyan]")


def agent_join(
    master: str = typer.Option(..., "--master", "-m", help="Master API URL"),
    key: str = typer.Option(..., "--key", "-k", help="Admin API Key"),
    role: str = typer.Option(
        "standalone", "--role", "-r", help="Node role (standalone, proxy, exit)"
    ),
    name: str = typer.Option(None, "--name", "-n", help="Node name (defaults to hostname)"),
):
    """Magic command to join a new node to the mesh network"""
    asyncio.run(_join(master, key, role, name))
