import asyncio

import typer
from rich.console import Console
from rich.table import Table

from .api import APIClient

app = typer.Typer(help="Manage and monitor physical hosts in the mesh")
console = Console()


async def _status():
    client = APIClient()
    try:
        # Get nodes list to iterate over them
        nodes = await client.list_nodes()

        table = Table(title="Mesh Host Status")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("CPU %", justify="right")
        table.add_column("Temp", justify="right")
        table.add_column("RAM %", justify="right")
        table.add_column("Disk %", justify="right")

        for node in nodes:
            try:
                metrics = await client.request("GET", f"/nodes/{node['id']}/host/metrics")
                temp = metrics.get("temperature")
                temp_str = f"{temp:.1f}°C" if temp is not None else "N/A"
                table.add_row(
                    str(node["id"]),
                    node["name"],
                    f"{metrics.get('cpu_usage_percent', 0.0):.1f}%",
                    temp_str,
                    f"{metrics.get('memory_usage_percent', 0.0):.1f}%",
                    f"{metrics.get('disk_usage_percent', 0.0):.1f}%",
                )
            except Exception:
                table.add_row(
                    str(node["id"]), node["name"], "[red]Offline[/red]", "N/A", "N/A", "N/A"
                )

        # Also check Master host metrics (special case, usually master is the API we talk to)
        try:
            master_metrics = await client.request("GET", "/host/metrics")
            temp = master_metrics.get("temperature")
            temp_str = f"{temp:.1f}°C" if temp is not None else "N/A"
            table.add_row(
                "M",
                "MASTER",
                f"{master_metrics.get('cpu_usage_percent', 0.0):.1f}%",
                temp_str,
                f"{master_metrics.get('memory_usage_percent', 0.0):.1f}%",
                f"{master_metrics.get('disk_usage_percent', 0.0):.1f}%",
            )
        except Exception:
            pass

        console.print(table)
    except Exception as e:
        console.print(f"[red]Error fetching host status: {e}[/red]")


@app.command("status")
def host_status():
    """Show real-time host metrics for all nodes"""
    asyncio.run(_status())


async def _clean(node_id: int | None = None):
    client = APIClient()
    try:
        if node_id:
            with console.status(f"[bold green]Cleaning host for node {node_id}..."):
                await client.request("POST", f"/nodes/{node_id}/host/clean")
            console.print(f"[green]Successfully triggered cleanup on node {node_id}[/green]")
        else:
            # Clean Master
            with console.status("[bold green]Cleaning Master host..."):
                await client.request("POST", "/host/clean")
            console.print("[green]Successfully triggered cleanup on Master host[/green]")

            # Clean all nodes
            nodes = await client.list_nodes()
            for node in nodes:
                try:
                    with console.status(
                        f"[bold green]Cleaning host for node {node['id']} ({node['name']})..."
                    ):
                        await client.request("POST", f"/nodes/{node['id']}/host/clean")
                    console.print(f"[green]Cleanup triggered on node {node['id']}[/green]")
                except Exception as e:
                    console.print(f"[red]Failed to clean node {node['id']}: {e}[/red]")
    except Exception as e:
        console.print(f"[red]Error during cleanup: {e}[/red]")


@app.command("clean")
def host_clean(
    node_id: int = typer.Option(
        None, help="Specific node ID to clean. If omitted, cleans all hosts."
    )
):
    """Trigger manual cleanup (Docker prune, logs rotation) on host(s)"""
    asyncio.run(_clean(node_id))
