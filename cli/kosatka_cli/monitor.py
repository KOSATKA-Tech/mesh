import asyncio

import typer
from rich.console import Console
from rich.live import Live
from rich.table import Table

from .api import APIClient

app = typer.Typer()
console = Console()


def generate_table(stats_data):
    table = Table(title="Mesh Real-time Monitor")
    table.add_column("Node ID", justify="right", style="cyan", no_wrap=True)
    table.add_column("Name", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("CPU % (last 5)", justify="center")
    table.add_column("RX (bps)", justify="right")
    table.add_column("TX (bps)", justify="right")

    for node in stats_data.get("nodes", []):
        cpu_history = node.get("cpu_history", [])
        cpu_str = " | ".join([f"{v:4.1f}" for v in cpu_history])
        if not cpu_str:
            cpu_str = "N/A"

        rx_history = node.get("rx_history", [])
        last_rx = rx_history[-1] if rx_history else -1

        tx_history = node.get("tx_history", [])
        last_tx = tx_history[-1] if tx_history else -1

        rx_str = f"{last_rx:,.0f}" if last_rx >= 0 else "N/A"
        tx_str = f"{last_tx:,.0f}" if last_tx >= 0 else "N/A"

        table.add_row(str(node["id"]), node["name"], node["status"], cpu_str, rx_str, tx_str)
    return table


async def monitor_loop():
    api = APIClient()
    with Live(generate_table({}), refresh_per_second=1, console=console) as live:
        while True:
            try:
                stats = await api.get_realtime_stats()
                live.update(generate_table(stats))
            except Exception:
                # On error, we could show something in the table, but for now just retry
                pass
            await asyncio.sleep(2)


@app.command("show")
def show():
    """Start real-time monitoring of the mesh"""
    try:
        asyncio.run(monitor_loop())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    app()
