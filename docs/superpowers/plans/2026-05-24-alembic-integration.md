# Alembic Integration (Master) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate Alembic for database migrations in the Kosatka Master service and remove manual "lightweight" migrations.

**Architecture:** Initialize Alembic in the `master/` directory, configure it to discover all models, and generate an initial migration that matches the current schema.

**Tech Stack:** Alembic, SQLAlchemy, FastAPI (Master service)

---

### Task 1: Environment Preparation and Alembic Initialization

**Files:**
- Create: `master/alembic.ini`
- Create: `master/alembic/` (directory)
- Modify: `master/kosatka_master/database.py` (ensure all models are imported)

- [ ] **Step 1: Update database.py to import all models**
Ensure `Event`, `GeositeEntry`, and `ClientRoutingProfile` are imported so Alembic can discover them.

```python
# master/kosatka_master/database.py

# ... (existing imports)
from .models.client import Client  # noqa: F401
from .models.node import Node  # noqa: F401
from .models.routing import RoutingPolicy, GeositeEntry, ClientRoutingProfile  # noqa: F401
from .models.subscription import Subscription  # noqa: F401
from .models.event import Event  # noqa: F401
# ...
```

- [ ] **Step 2: Initialize Alembic**
Run `alembic init alembic` inside the `master/` directory.

Run: `cd master && alembic init alembic`
Expected: `alembic.ini` and `alembic/` directory created.

- [ ] **Step 3: Commit initialization**
```bash
git add master/alembic.ini master/alembic/ master/kosatka_master/database.py
git commit -m "chore: initialize alembic for master"
```

### Task 2: Configure Alembic for the Project

**Files:**
- Modify: `master/alembic.ini`
- Modify: `master/alembic/env.py`

- [ ] **Step 1: Configure alembic.ini to use environment variables**
We'll modify `env.py` to get the URL from our config instead of hardcoding it in `alembic.ini`.

- [ ] **Step 2: Configure alembic/env.py**
Import `Base` and `settings` to configure the migration engine.

```python
# master/alembic/env.py
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# 1. Import your models' metadata
from kosatka_master.database import Base
# 2. Import your settings
from kosatka_master.config import settings

# this is the Alembic Config object, which provides access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 3. Set target_metadata
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = settings.database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "pyformat"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Use settings.database_url instead of config.get_main_option("sqlalchemy.url")
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings.database_url

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 3: Commit configuration**
```bash
git add master/alembic/env.py
git commit -m "config: setup alembic env.py with project settings"
```

### Task 3: Create Initial Migration

**Files:**
- Create: `master/alembic/versions/XXXX_initial_schema.py`

- [ ] **Step 1: Generate initial migration**
Run `alembic revision --autogenerate -m "initial_schema"` inside `master/`.

Run: `cd master && PYTHONPATH=. alembic revision --autogenerate -m "initial_schema"`
Expected: A new file in `master/alembic/versions/`.

- [ ] **Step 2: Verify the migration content**
Read the generated file and ensure it matches the expected tables: `nodes`, `clients`, `subscriptions`, `routing_policies`, `geosite_entries`, `client_routing_profiles`, `events`.

- [ ] **Step 3: Commit initial migration**
```bash
git add master/alembic/versions/
git commit -m "feat: initial alembic migration"
```

### Task 4: Clean up main.py

**Files:**
- Modify: `master/kosatka_master/main.py`

- [ ] **Step 1: Remove manual migrations**
Delete `_LIGHTWEIGHT_MIGRATIONS`, `_apply_lightweight_migrations`, and its call in `lifespan`.

- [ ] **Step 2: Commit cleanup**
```bash
git add master/kosatka_master/main.py
git commit -m "refactor: remove manual migrations in favor of alembic"
```

### Task 5: Verification and Testing

**Files:**
- Create: `master/tests/test_migrations.py`

- [ ] **Step 1: Write a test for migrations**
Create a test that runs `alembic upgrade head` on a temporary database.

```python
# master/tests/test_migrations.py
import pytest
import os
from alembic.config import Config
from alembic import command

def test_migrations_upgrade_head():
    # Use a temporary sqlite database
    db_file = "test_migrations.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    os.environ["KOSATKA_DATABASE_URL"] = f"sqlite+aiosqlite:///./{db_file}"

    alembic_cfg = Config("alembic.ini")
    # No need to change sqlalchemy.url in Config because env.py uses settings.database_url

    try:
        command.upgrade(alembic_cfg, "head")
    finally:
        if os.path.exists(db_file):
            os.remove(db_file)
```

- [ ] **Step 2: Run the test**
Run: `cd master && pytest tests/test_migrations.py`
Expected: PASS

- [ ] **Step 3: Final Commit**
```bash
git add master/tests/test_migrations.py
git commit -m "test: add migration verification test"
```
