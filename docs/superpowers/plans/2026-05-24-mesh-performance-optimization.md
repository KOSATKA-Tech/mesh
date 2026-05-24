# Kosatka Mesh Performance & Scalability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enhance Master performance with connection pooling and migrations, and implement autonomous dynamic traffic shaping on Agents to support low-end VPS.

**Architecture:**
- **Master:** Singleton `httpx.AsyncClient`, Alembic for migrations, and trend-based load balancing.
- **Agent:** Background Metric Collector with EMA smoothing, TC HTB engine for shaping, and a Penalty Box for heavy hitters.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, httpx, psutil, Linux `tc` (Traffic Control).

---

### Task 1: Alembic Integration (Master)

**Files:**
- Create: `master/alembic.ini`
- Create: `master/alembic/env.py`, `master/alembic/versions/initial_migration.py`
- Modify: `master/kosatka_master/main.py`

- [ ] **Step 1: Initialize Alembic**
Run: `cd master && alembic init alembic`

- [ ] **Step 2: Configure `alembic.ini` and `env.py`**
Ensure `env.py` imports `Base` from `kosatka_master.database` and `Node`, `Client`, etc. from `models`.

- [ ] **Step 3: Create initial migration**
Run: `alembic revision --autogenerate -m "initial_schema"`

- [ ] **Step 4: Update `main.py` to remove manual migrations**
Replace `_apply_lightweight_migrations` logic with a reminder to use alembic or a production-safe auto-upgrade if requested.

- [ ] **Step 5: Verify migration runs**
Run: `alembic upgrade head`

- [ ] **Step 6: Commit**
`git commit -m "feat(master): add alembic migrations"`

---

### Task 2: Connection Pooling with HTTP/2 (Master)

**Files:**
- Modify: `master/kosatka_master/api/v1/clients.py`
- Modify: `master/kosatka_master/services/node_manager.py`

- [ ] **Step 1: Implement Global AsyncClient**
In `master/kosatka_master/security.py` or a new `master/kosatka_master/http_client.py`:
```python
import httpx
from contextlib import asynccontextmanager

_client: httpx.AsyncClient | None = None

@asynccontextmanager
async def get_http_client():
    global _client
    if _client is None:
        _client = httpx.AsyncClient(http2=True, timeout=10.0, limits=httpx.Limits(max_connections=100))
    yield _client
```

- [ ] **Step 2: Refactor `_call_agent` in `clients.py`**
Use the global client instead of creating a new one in a context manager.

- [ ] **Step 3: Refactor `sync_all_nodes` in `node_manager.py`**
Use the global client for concurrent probes.

- [ ] **Step 4: Commit**
`git commit -m "perf(master): implement connection pooling with http/2"`

---

### Task 3: Metric Collector with EMA Smoothing (Agent)

**Files:**
- Create: `agent/kosatka_agent/metrics.py`
- Modify: `agent/kosatka_agent/main.py`

- [ ] **Step 1: Implement `MetricsCollector` class**
```python
import psutil
import time

class MetricsCollector:
    def __init__(self, alpha=0.3):
        self.alpha = alpha
        self.ema_cpu = None
        self.ema_bw = None

    def get_metrics(self):
        # Smoothing logic
        cpu = psutil.cpu_percent()
        if self.ema_cpu is None: self.ema_cpu = cpu
        else: self.ema_cpu = self.alpha * cpu + (1 - self.alpha) * self.ema_cpu
        return {"cpu_ema": self.ema_cpu, "load_avg": psutil.getloadavg()[0]}
```

- [ ] **Step 2: Start collector in Agent lifespan**
Add as a background task in `agent/kosatka_agent/main.py`.

- [ ] **Step 3: Commit**
`git commit -m "feat(agent): add background metrics collector with EMA"`

---

### Task 4: TC HTB Engine & Shaping Logic (Agent)

**Files:**
- Create: `agent/kosatka_agent/shaper.py`

- [ ] **Step 1: Implement `TrafficShaper`**
Wrapper for `tc` commands to setup HTB root, classes (1:1 - priority, 1:10 - throttled).

- [ ] **Step 2: Implement `apply_throttle(ip)` and `remove_throttle(ip)`**
Use `tc filter add/del` to move specific client IPs between classes.

- [ ] **Step 3: Commit**
`git commit -m "feat(agent): add tc-based traffic shaping engine"`

---

### Task 5: Heavyweight Detection & Penalty Box (Agent)

**Files:**
- Modify: `agent/kosatka_agent/metrics.py`
- Modify: `agent/kosatka_agent/shaper.py`

- [ ] **Step 1: Logic to identify heavy hitters**
Compare peer byte counts over 10s intervals.

- [ ] **Step 2: Implement Penalty Box**
Use a dict `penalty_end_times = {ip: end_timestamp}`.
In the metrics loop: if IP in penalty and now < end, keep throttled. If now > end, release.

- [ ] **Step 3: Commit**
`git commit -m "feat(agent): implement dynamic heavyweight detection and penalty box"`

---

### Task 6: Trend-Aware Balancing (Master)

**Files:**
- Modify: `master/kosatka_master/models/node.py` (add `node_stats` table)
- Modify: `master/kosatka_master/services/node_manager.py`

- [ ] **Step 1: Create `NodeStat` model**
Store `node_id`, `cpu_load`, `bw_util`, `timestamp`.

- [ ] **Step 2: Update `_pick_node` in `clients.py`**
Query last 5 stats per candidate node. Calculate trend. Penalty for rising load.

- [ ] **Step 3: Commit**
`git commit -m "feat(master): implement trend-aware load balancing"`
