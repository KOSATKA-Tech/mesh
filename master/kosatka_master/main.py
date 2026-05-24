import os
import tarfile
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api.v1.router import api_router
from .database import Base, engine
from .http_client import http_client_lifespan
from .scheduler import scheduler, setup_scheduler
from .security import get_api_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables if they don't exist. This is safe for an MVP; for
    # production, prefer Alembic migrations (not yet set up in this repo).
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # setup_scheduler() registers sync_nodes_job + check_expirations_job
    # and calls scheduler.start() internally. Calling scheduler.start() here
    # directly would leave the scheduler jobless.
    setup_scheduler()
    async with http_client_lifespan():
        try:
            yield
        finally:
            scheduler.shutdown()


app = FastAPI(title="Kosatka Mesh Master", lifespan=lifespan)

# Mount static directory for install.sh
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


def _resolve_ansible_dir() -> Path:
    """Locate the ansible/ tree regardless of how the master is deployed.

    The source tree checkout has ``ansible/`` at the repo root (three
    parents up from this module), while the Docker image copies it to
    ``/app/ansible`` and sets ``KOSATKA_ANSIBLE_DIR`` accordingly. We
    prefer the explicit env var, then fall back to the dev layout.
    """
    explicit = os.environ.get("KOSATKA_ANSIBLE_DIR")
    if explicit and Path(explicit).is_dir():
        return Path(explicit)
    repo_layout = Path(__file__).parent.parent.parent / "ansible"
    if repo_layout.is_dir():
        return repo_layout
    docker_layout = Path("/app/ansible")
    if docker_layout.is_dir():
        return docker_layout
    # Surface a clear error instead of silently packaging an empty tar.
    raise RuntimeError(
        "Unable to locate the ansible/ directory. Set KOSATKA_ANSIBLE_DIR "
        "to an absolute path or ensure the directory is mounted into the "
        "container."
    )


@app.get("/api/v1/static/ansible.tar.gz")
async def download_ansible_playbooks(
    background_tasks: BackgroundTasks,
    _: str = Depends(get_api_key),
):
    """Pack the ansible directory and serve it as a tarball.

    Requires the same ``X-Kosatka-Key`` header as the rest of ``/api/v1/*``.
    The ansible tree contains the agent self-bootstrap playbooks and
    must not be downloadable by anonymous clients on the public internet.
    ``install.sh`` forwards the operator's ``--token`` value as the
    header so the existing bootstrap flow keeps working.
    """
    ansible_dir = _resolve_ansible_dir()

    fd, temp_path = tempfile.mkstemp(suffix=".tar.gz")
    os.close(fd)

    with tarfile.open(temp_path, "w:gz") as tar:
        tar.add(str(ansible_dir), arcname=".")

    background_tasks.add_task(os.remove, temp_path)

    return FileResponse(temp_path, filename="ansible.tar.gz")


app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
