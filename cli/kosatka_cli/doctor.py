import httpx
from rich.console import Console

from .api import APIClient
from .config import load_config

console = Console()


async def run_diagnostics():
    config = load_config()
    console.print("[bold cyan]Kosatka Doctor - Diagnostics[/bold cyan]\n")

    # 1. Check config
    console.print("[yellow]Checking configuration...[/yellow]")
    if not config.api_key:
        console.print(
            "[red]✗ API Key not set. Use 'kosatka login' or edit ~/.kosatka/config.json[/red]"
        )
    else:
        console.print("[green]✓ API Key found[/green]")

    # 2. Check Master connectivity
    console.print(f"[yellow]Checking connectivity to {config.base_url}...[/yellow]")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{config.base_url}/health")
            if response.status_code == 200:
                console.print("[green]✓ Master is reachable (status 200)[/green]")
            else:
                console.print(f"[red]✗ Master returned status {response.status_code}[/red]")
    except Exception as e:
        console.print(f"[red]✗ Cannot reach Master: {e}[/red]")

    # 3. Check API Authentication
    if config.api_key:
        console.print("[yellow]Checking API authentication...[/yellow]")
        api = APIClient()
        try:
            await api.get_stats()
            console.print("[green]✓ API authentication successful[/green]")
        except Exception as e:
            console.print(f"[red]✗ API authentication failed: {e}[/red]")

    # 4. Check Nodes Host Status
    console.print("[yellow]Checking nodes host status...[/yellow]")
    api = APIClient()
    try:
        nodes = await api.list_nodes()
        for node in nodes:
            try:
                metrics = await api.request("GET", f"/nodes/{node['id']}/host/metrics")
                disk = metrics.get("disk_usage_percent", 0.0)
                if disk > 90:
                    console.print(
                        f"[red]✗ Node '{node['name']}' has low disk space: {disk}% used[/red]"
                    )
                else:
                    console.print(f"[green]✓ Node '{node['name']}' host is healthy[/green]")
            except Exception:
                console.print(f"[red]✗ Cannot fetch host metrics for node '{node['name']}'[/red]")
    except Exception as e:
        console.print(f"[red]✗ Cannot list nodes: {e}[/red]")
