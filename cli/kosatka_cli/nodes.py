import asyncio

import typer
from rich.console import Console
from rich.table import Table

from .api import APIClient

app = typer.Typer(help="Manage Kosatka nodes")
console = Console()


async def _list():
    client = APIClient()
    try:
        nodes = await client.list_nodes()
        table = Table(title="Kosatka Nodes")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Address", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Provider", style="blue")

        for node in nodes:
            table.add_row(
                str(node["id"]),
                node["name"],
                node["address"],
                node["status"],
                node["provider_type"],
            )

        console.print(table)
    except Exception as e:
        console.print(f"[red]Error listing nodes: {e}[/red]")


@app.command("list")
def list_nodes():
    """List all registered nodes"""
    asyncio.run(_list())


async def _register(name: str, address: str, provider: str, api_key: str | None = None):
    client = APIClient()
    try:
        node = await client.register_node(name, address, provider, api_key)
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
):
    """Register a new node"""
    if "://" not in address:
        address = f"http://{address}"
    asyncio.run(_register(name, address, provider, api_key))


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
