import typer
from rich.console import Console

from . import config, deploy, nodes

app = typer.Typer(help="Kosatka Mesh CLI - Manage your global VPN mesh")
console = Console()

master_app = typer.Typer(help="Manage and run Kosatka Master service")
agent_app = typer.Typer(help="Manage and run Kosatka Agent service")

app.add_typer(nodes.app, name="nodes")
app.add_typer(deploy.app, name="deploy")
app.add_typer(master_app, name="master")
app.add_typer(agent_app, name="agent")


@master_app.command("run")
def master_run(
    host: str = typer.Option("0.0.0.0", help="Bind host"),
    port: int = typer.Option(8000, help="Bind port"),
    reload: bool = typer.Option(False, help="Enable auto-reload"),
):
    """Run the Kosatka Master service"""
    import uvicorn

    console.print(f"[bold green]Starting Kosatka Master on {host}:{port}[/bold green]")
    uvicorn.run("kosatka_master.main:app", host=host, port=port, reload=reload)


@agent_app.command("run")
def agent_run(
    host: str = typer.Option("0.0.0.0", help="Bind host"),
    port: int = typer.Option(8010, help="Bind port"),
    reload: bool = typer.Option(False, help="Enable auto-reload"),
):
    """Run the Kosatka Agent service"""
    import uvicorn

    console.print(f"[bold green]Starting Kosatka Agent on {host}:{port}[/bold green]")
    uvicorn.run("kosatka_agent.main:app", host=host, port=port, reload=reload)


@app.command()
def login(
    base_url: str = typer.Option("http://localhost:8000", help="Master API Base URL"),
    api_key: str = typer.Argument(..., help="Admin API Key"),
):
    """Log in to a Kosatka Master instance"""
    if "://" not in base_url:
        base_url = f"http://{base_url}"
    cfg = config.Config(base_url=base_url, api_key=api_key)
    config.save_config(cfg)
    console.print(f"[green]Successfully saved configuration to {config.CONFIG_FILE}[/green]")


@app.command()
def info():
    """Show current CLI configuration"""
    cfg = config.load_config()
    console.print(f"Base URL: [cyan]{cfg.base_url}[/cyan]")
    console.print(f"API Key: [cyan]{'Set' if cfg.api_key else 'Not Set'}[/cyan]")


@app.command()
def doctor():
    """Run diagnostic checks on your Kosatka environment"""
    import asyncio

    from .doctor import run_diagnostics

    asyncio.run(run_diagnostics())


if __name__ == "__main__":
    app()
