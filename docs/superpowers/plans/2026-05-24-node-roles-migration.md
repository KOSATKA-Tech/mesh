# Master Model & Migration (Node Roles) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update Node model and generate an Alembic migration to support server roles and chaining.

**Architecture:** Extend the `Node` model with `role` (standalone/proxy/exit) and `upstream_id` (self-referential FK) to enable Stealth Chaining.

**Tech Stack:** SQLAlchemy, Alembic, SQLite.

---

### Task 1: Research & Setup

**Files:**
- Research: `master/kosatka_master/models/node.py`
- Research: `master/alembic/versions/`

- [ ] **Step 1: Verify current environment**
Run: `ls -F` in `master/` to confirm files.

### Task 2: Write Failing Test

**Files:**
- Create: `master/tests/test_node_roles.py`

- [ ] **Step 1: Write the failing test**
```python
import pytest
from sqlalchemy import select
from kosatka_master.models.node import Node

@pytest.mark.asyncio
async def test_node_roles_and_upstream(db_session):
    # Create an exit node
    exit_node = Node(
        name="exit-node",
        address="1.1.1.1",
        provider_type="agent",
        role="exit"
    )
    db_session.add(exit_node)
    await db_session.commit()
    await db_session.refresh(exit_node)

    # Create a proxy node pointing to the exit node
    proxy_node = Node(
        name="proxy-node",
        address="2.2.2.2",
        provider_type="agent",
        role="proxy",
        upstream_id=exit_node.id
    )
    db_session.add(proxy_node)
    await db_session.commit()
    await db_session.refresh(proxy_node)

    # Verify retrieval
    stmt = select(Node).where(Node.name == "proxy-node")
    result = await db_session.execute(stmt)
    retrieved_proxy = result.scalar_one()

    assert retrieved_proxy.role == "proxy"
    assert retrieved_proxy.upstream_id == exit_node.id
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest master/tests/test_node_roles.py -v`
Expected: FAIL with `AttributeError: type object 'Node' has no attribute 'role'` (or similar)

### Task 3: Implement Model Changes

**Files:**
- Modify: `master/kosatka_master/models/node.py`

- [ ] **Step 1: Add role and upstream_id to Node model**
Update `Node` class:
```python
class Node(Base):
    __tablename__ = "nodes"

    # ... existing fields ...
    role: Mapped[str] = mapped_column(String(50), default="standalone")
    upstream_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id"), nullable=True)
    # ...
```

### Task 4: Generate and Apply Migration

**Files:**
- Create: `master/alembic/versions/<hash>_add_node_roles.py`

- [ ] **Step 1: Generate migration**
Run: `cd master && alembic revision --autogenerate -m "add_node_roles"`

- [ ] **Step 2: Verify migration content**
Inspect the generated file in `master/alembic/versions/`.

- [ ] **Step 3: Apply migration**
Run: `cd master && alembic upgrade head`

### Task 5: Verify Implementation

**Files:**
- Test: `master/tests/test_node_roles.py`

- [ ] **Step 1: Run the test to verify it passes**
Run: `pytest master/tests/test_node_roles.py -v`
Expected: PASS

- [ ] **Step 2: Commit changes**
Run: `git add master/kosatka_master/models/node.py master/alembic/versions/ master/tests/test_node_roles.py`
Run: `git commit -m "feat(master): add node roles and upstream_id for chaining"`
