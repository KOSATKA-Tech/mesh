import asyncio

import click
import typer
from rich.console import Console
from rich.table import Table

from . import config
from .api import APIClient
from .dns import get_dns_provider

app = typer.Typer(help="Manage Kosatka nodes")
console = Console()


async def _list(role: str | None = None):
    client = APIClient()
    try:
        nodes = await client.list_nodes(role=role)
        table = Table(title=f"Kosatka Nodes{' (' + role + ')' if role else ''}")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Address", style="green")
        table.add_column("Role", style="cyan")
        table.add_column("Status", style="yellow")
        table.add_column("Provider", style="blue")

        for node in nodes:
            role_str = node.get("role", "standalone")
            if role_str == "proxy" and node.get("upstream_id"):
                role_str = f"proxy -> {node['upstream_id']}"

            table.add_row(
                str(node["id"]),
                node["name"],
                node["address"],
                role_str,
                node["status"],
                node["provider_type"],
            )

        console.print(table)
    except Exception as e:
        console.print(f"[red]Error listing nodes: {e}[/red]")


@app.command("list")
def list_nodes(
    role: str = typer.Option(None, help="Filter nodes by role (standalone, proxy, exit)"),
):
    """List all registered nodes"""
    asyncio.run(_list(role))


async def _register(
    name: str,
    address: str,
    provider: str,
    api_key: str | None = None,
    role: str = "standalone",
    upstream_id: int | None = None,
):
    client = APIClient()
    cfg = config.load_config()
    try:
        # DNS Automation
        if cfg.base_domain:
            # Generate a sub-domain based on node name
            # e.g. node1 -> node1.ub.kosatka.tech
            full_domain = f"{name.lower()}.{cfg.base_domain.strip('.')}"
            dns = get_dns_provider(cfg.model_dump())

            # Extract IP from address (it might be http://IP or just IP)
            import urllib.parse

            parsed = urllib.parse.urlparse(address)
            ip_only = (
                parsed.hostname
                or address.replace("http://", "").replace("https://", "").split(":")[0]
            )

            with console.status(f"[bold green]Provisioning DNS record for {full_domain}..."):
                success = await dns.create_a_record(full_domain, ip_only)
                if success:
                    console.print(f"[green]DNS record created: {full_domain} -> {ip_only}[/green]")
                    # Use the domain as the address for API calls (default to https if SSL is expected)
                    address = f"https://{full_domain}"
                else:
                    console.print("[red]Failed to create DNS record automatically.[/red]")

        # Interactive role selection if not provided
        if not role:
            role = typer.prompt(
                "Select node role",
                type=click.Choice(["standalone", "proxy", "exit"]),
                default="standalone",
            )

        # Interactive upstream selection for proxies
        if role == "proxy" and not upstream_id:
            exit_nodes = await client.list_nodes(role="exit")
            if not exit_nodes:
                console.print(
                    "[red]Error: No Exit nodes available. A proxy node requires an exit node.[/red]"
                )
                return

            table = Table(title="Available Exit Nodes")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="magenta")
            table.add_column("Address", style="green")
            for n in exit_nodes:
                table.add_row(str(n["id"]), n["name"], n["address"])
            console.print(table)

            upstream_id = typer.prompt("Enter the ID of the Exit node to use as upstream", type=int)

        node = await client.register_node(
            name, address, provider, api_key, role=role, upstream_id=upstream_id
        )
        console.print(f"[green]Successfully registered node '{name}' with ID {node['id']}[/green]")
    except Exception as e:
        console.print(f"[red]Error registering node: {e}[/red]")


@app.command("register")
@app.command("add")
def register_node(
    name: str = typer.Argument(..., help="Name of the node"),
    address: str = typer.Argument(..., help="IP or hostname of the node"),
    provider: str = typer.Option("agent", help="Provider type (agent, wireguard, etc.)"),
    api_key: str = typer.Option(None, "--api-key", "--key", "-k", help="API key for the agent"),
    role: str = typer.Option(
        None,
        help="Node role: standalone (standard), proxy (relay), exit (termination for proxies)",
    ),
    upstream_id: int = typer.Option(None, "--upstream-id", help="ID of the upstream exit node"),
):
    """Register a new node"""
    if "://" not in address:
        address = f"http://{address}"
    asyncio.run(_register(name, address, provider, api_key, role, upstream_id))


async def _health(node_id: int):
    client = APIClient()
    try:
        health = await client.get_node_health(node_id)
        console.print(f"Health for node {node_id}:")
        console.print(health)
    except Exception as e:
        console.print(f"[red]Error getting node health: {e}[/red]")


@app.command("health")
def node_health(node_id: int = typer.Argument(..., help="ID of the node")):
    """Get health status of a node"""
    asyncio.run(_health(node_id))


async def _provision(name: str, protocol: str):
    client = APIClient()
    try:
        with console.status(f"[bold green]Provisioning {protocol} profile for {name}..."):
            profile = await client.provision_client(name, protocol)
        console.print(
            f"[green]Successfully provisioned profile on node {profile['node_id']}[/green]"
        )
        console.print("\n[bold]VPN Configuration:[/bold]")
        console.print(profile.get("config_text", "No config text available"))
    except Exception as e:
        console.print(f"[red]Error provisioning client: {e}[/red]")


@app.command("provision")
def provision_client(
    name: str = typer.Argument(..., help="Name for the VPN profile"),
    protocol: str = typer.Option("amneziawg", help="VPN Protocol (amneziawg, wireguard, vless)"),
):
    """Find a node and provision a new VPN profile"""
    asyncio.run(_provision(name, protocol))
