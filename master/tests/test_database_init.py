"""Regression tests for ``kosatka_master.database`` startup behaviour.

The original deployment failure (`sqlite3.OperationalError: unable to open
database file`) happened because ``KOSATKA_DATABASE_URL=...///./data/kosatka.db``
pointed at a directory that didn't exist yet \u2014 SQLite refuses to create
the parent. The auto-mkdir in ``database._ensure_sqlite_directory`` keeps
out-of-the-box ``kosatka-mesh master run`` working without forcing the
operator to ``mkdir data`` first.
"""

from __future__ import annotations

import importlib
import sys


def _reimport_database_module() -> object:
    """Drop cached config + database modules and reimport.

    ``Settings`` reads the env once at import; we need a clean reload so
    the patched ``KOSATKA_DATABASE_URL`` actually takes effect.
    """
    sys.modules.pop("kosatka_master.config", None)
    sys.modules.pop("kosatka_master.database", None)
    return importlib.import_module("kosatka_master.database")


def test_sqlite_parent_directory_is_auto_created(tmp_path, monkeypatch):
    """Importing ``database`` with a sqlite URL should mkdir the parent."""
    nested = tmp_path / "nested" / "subdir"
    db_file = nested / "kosatka.db"
    assert not nested.exists()

    monkeypatch.setenv("KOSATKA_DATABASE_URL", f"sqlite+aiosqlite:///{db_file}")
    _reimport_database_module()

    assert nested.is_dir(), (
        "database.py should have mkdir -p'd the sqlite parent so "
        "sqlite3.connect doesn't 'unable to open database file'"
    )


def test_postgres_url_skips_filesystem_mkdir(monkeypatch):
    """Non-sqlite URLs short-circuit the helper without touching the filesystem."""
    monkeypatch.setenv(
        "KOSATKA_DATABASE_URL", "postgresql+asyncpg://kosatka:kosatka@postgres:5432/kosatka"
    )
    mod = _reimport_database_module()
    # Engine is constructed lazily in this module, but a postgres URL
    # must at least produce a usable Engine object \u2014 if the helper
    # tried to mkdir on a postgres URL we'd raise here on the parsed
    # path components.
    assert mod.engine is not None


def test_in_memory_sqlite_does_not_break(monkeypatch):
    """``:memory:`` is a valid SQLite path with no parent directory \u2014 must not crash."""
    monkeypatch.setenv("KOSATKA_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    mod = _reimport_database_module()
    assert mod.engine is not None
