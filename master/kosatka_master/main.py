import logging
import os
import tarfile
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import models  # noqa: F401
from .api.v1.dashboard import router as dashboard_router
from .api.v1.limiter import setup_rate_limiting
from .api.v1.router import api_router
from .api.v1.subscriptions import public_router as subscriptions_public_router
from .config import settings
from .database import Base, engine
from .http_client import http_client_lifespan
from .instances import host_monitor
from .scheduler import scheduler, setup_scheduler
from .security import get_api_key

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed SystemConfig from settings if empty
    import json

    from .models.alert import SystemConfig

    async with AsyncSession(engine) as session:
        res = await session.execute(select(SystemConfig))
        if not res.scalars().first():
            config_items = [
                SystemConfig(key="smtp_host", value=json.dumps(settings.smtp_host)),
                SystemConfig(key="smtp_port", value=json.dumps(settings.smtp_port)),
                SystemConfig(key="smtp_user", value=json.dumps(settings.smtp_user)),
                SystemConfig(key="smtp_password", value=json.dumps(settings.smtp_password)),
                SystemConfig(key="smtp_from", value=json.dumps(settings.smtp_from)),
                SystemConfig(key="bot_username", value=json.dumps(settings.bot_username)),
                SystemConfig(key="base_domain", value=json.dumps(settings.domain)),
            ]
            session.add_all(config_items)
            await session.commit()

    # Start services
    host_monitor.start()

    # setup_scheduler() registers sync_nodes_job + check_expirations_job
    # and calls scheduler.start() internally. Calling scheduler.start() here
    # directly would leave the scheduler jobless.
    setup_scheduler()

    if settings.auto_https and settings.domain:
        from .services.dns.https_manager import start_https_proxy

        start_https_proxy(settings.domain, 8000)

    async with http_client_lifespan():
        try:
            yield
        finally:
            await host_monitor.stop()
            scheduler.shutdown()


app = FastAPI(title="Kosatka Mesh Master", lifespan=lifespan)
setup_rate_limiting(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _resolve_ansible_dir() -> Path:
    """Locate the ansible/ tree regardless of how the master is deployed."""
    explicit = os.environ.get("KOSATKA_ANSIBLE_DIR")
    if explicit and Path(explicit).is_dir():
        return Path(explicit)
    repo_layout = Path(__file__).parent.parent.parent / "ansible"
    if repo_layout.is_dir():
        return repo_layout
    docker_layout = Path("/app/ansible")
    if docker_layout.is_dir():
        return docker_layout
    raise RuntimeError("Unable to locate the ansible/ directory.")


@app.get("/api/v1/static/ansible.tar.gz")
async def download_ansible_playbooks(
    background_tasks: BackgroundTasks,
    _: str = Depends(get_api_key),
):
    """Pack the ansible directory and serve it as a tarball."""
    ansible_dir = _resolve_ansible_dir()
    fd, temp_path = tempfile.mkstemp(suffix=".tar.gz")
    os.close(fd)
    with tarfile.open(temp_path, "w:gz") as tar:
        tar.add(str(ansible_dir), arcname=".")
    background_tasks.add_task(os.remove, temp_path)
    return FileResponse(temp_path, filename="ansible.tar.gz")


# Include Routers
app.include_router(api_router, prefix="/api/v1")
app.include_router(subscriptions_public_router, prefix="/sub")
app.include_router(dashboard_router)

# Serve Admin UI
static_dir = Path(__file__).parent / "static"
admin_dir = static_dir / "admin"

if settings.serve_ui and admin_dir.exists():
    # Use StaticFiles for everything except the root HTML
    # This handles MIME types correctly for CSS/JS
    app.mount("/admin/assets", StaticFiles(directory=str(admin_dir / "assets")), name="assets")

    @app.get("/admin/{full_path:path}")
    async def serve_admin(full_path: str):
        # 1. If requesting a file in the admin root (favicon, etc), serve it
        file_path = admin_dir / full_path
        if file_path.is_file():
            return FileResponse(file_path)

        # 2. Otherwise serve index.html for SPA routing
        return FileResponse(admin_dir / "index.html")

    @app.get("/")
    async def redirect_to_admin():
        return RedirectResponse(url="/admin/")

else:
    logger.warning(f"Admin directory {admin_dir} not found. UI will not be served.")


@app.get("/health")
async def health():
    return {"status": "ok"}
