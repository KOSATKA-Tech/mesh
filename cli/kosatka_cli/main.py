import typer
from rich.console import Console

from . import config, deploy, host, monitor, nodes
from .join import agent_join

app = typer.Typer(help="Kosatka Mesh CLI - Manage your global VPN mesh")
console = Console()

master_app = typer.Typer(help="Manage and run Kosatka Master service")
agent_app = typer.Typer(help="Manage and run Kosatka Agent service")

app.add_typer(nodes.app, name="nodes")
app.add_typer(deploy.app, name="deploy")
app.add_typer(monitor.app, name="monitor")
app.add_typer(host.app, name="host")
app.add_typer(master_app, name="master")
app.add_typer(agent_app, name="agent")


@agent_app.command("join")
def join(
    master: str = typer.Option(..., "--master", "-m", help="Master API URL"),
    key: str = typer.Option(..., "--key", "-k", help="Admin API Key"),
    role: str = typer.Option("standalone", "--role", "-r", help="Node role"),
    name: str = typer.Option(None, "--name", "-n", help="Node name"),
):
    """Magic command to join a new node to the mesh network"""
    agent_join(master, key, role, name)


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
    cfg = config.load_config()
    cfg.base_url = base_url
    cfg.api_key = api_key
    config.save_config(cfg)
    console.print(f"[green]Successfully saved configuration to {config.CONFIG_FILE}[/green]")


@app.command("dns-setup")
def dns_setup(
    provider: str = typer.Option("manual", help="DNS provider: manual, beget"),
    base_domain: str = typer.Option(None, help="Base domain (e.g., ub.kosatka.tech)"),
):
    """Configure DNS provider and base domain for SSL/HTTPS automation"""
    cfg = config.load_config()
    cfg.dns_provider = provider
    if base_domain:
        cfg.base_domain = base_domain

    if provider == "beget":
        cfg.beget_login = typer.prompt("Beget API Login")
        cfg.beget_api_key = typer.prompt("Beget API Key", hide_input=True)

    if not cfg.base_domain:
        cfg.base_domain = typer.prompt("Base domain (e.g., ub.kosatka.tech)")

    config.save_config(cfg)
    console.print("[green]DNS configuration saved.[/green]")


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
