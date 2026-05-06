import os
import tarfile
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from .api.v1.router import api_router
from .database import Base, engine
from .scheduler import scheduler, setup_scheduler

# Columns added to existing tables by recent feature work. `create_all`
# only creates missing tables — it cannot `ALTER TABLE … ADD COLUMN` on
# tables that already exist, so deployments that predate these columns
# would otherwise hit "no such column: nodes.api_key" on every SELECT.
# Until Alembic is in place, run an idempotent ADD COLUMN on startup.
_LIGHTWEIGHT_MIGRATIONS: list[tuple[str, str, str]] = [
    ("nodes", "api_key", "VARCHAR(255)"),
]


async def _apply_lightweight_migrations() -> None:
    """Add columns that were introduced after the first deployment.

    Supports both SQLite (``PRAGMA table_info``) and Postgres
    (``information_schema``) so the same code path works for the new
    ``docker-compose.master.yml`` Postgres deployment and for local
    ``sqlite+aiosqlite`` development.
    """
    dialect = engine.dialect.name  # 'sqlite' | 'postgresql' | ...
    async with engine.begin() as conn:
        for table, column, sql_type in _LIGHTWEIGHT_MIGRATIONS:
            if dialect == "sqlite":
                result = await conn.exec_driver_sql(f"PRAGMA table_info({table})")
                existing_columns = {row[1] for row in result.fetchall()}
            else:
                result = await conn.exec_driver_sql(
                    "SELECT column_name FROM information_schema.columns "
                    f"WHERE table_name = '{table}'"
                )
                existing_columns = {row[0] for row in result.fetchall()}
            if column not in existing_columns:
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables if they don't exist. This is safe for an MVP; for
    # production, prefer Alembic migrations (not yet set up in this repo).
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await _apply_lightweight_migrations()

    # setup_scheduler() registers sync_nodes_job + check_expirations_job
    # and calls scheduler.start() internally. Calling scheduler.start() here
    # directly would leave the scheduler jobless.
    setup_scheduler()
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
async def download_ansible_playbooks(background_tasks: BackgroundTasks):
    """Pack the ansible directory and serve it as a tarball."""
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
