from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings


class Base(DeclarativeBase):
    pass


# Import all models to ensure they are registered with Base.metadata
from .models.client import Client  # noqa: F401, E402
from .models.node import Node  # noqa: F401, E402
from .models.routing import RoutingPolicy  # noqa: F401, E402
from .models.subscription import Subscription  # noqa: F401, E402


def _ensure_sqlite_directory(database_url: str) -> None:
    """``sqlite3.connect`` raises ``unable to open database file`` when the
    parent directory does not exist. Creating it on import keeps the
    out-of-the-box ``KOSATKA_DATABASE_URL=sqlite+aiosqlite:///./data/kosatka.db``
    default working without forcing operators to ``mkdir data`` by hand
    before ``kosatka-mesh master run``. No-op for non-sqlite URLs.
    """
    if not database_url.startswith("sqlite"):
        return
    # Strip the SQLAlchemy dialect prefix (``sqlite+aiosqlite:///``,
    # ``sqlite:///``) and the leading slash that delimits the SQLite path.
    _, _, raw = database_url.partition(":///")
    if not raw or raw == ":memory:":
        return
    db_path = Path(raw)
    parent = db_path.parent
    if parent and str(parent) not in ("", "."):
        parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_directory(settings.database_url)

engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db():
    async with SessionLocal() as session:
        yield session
