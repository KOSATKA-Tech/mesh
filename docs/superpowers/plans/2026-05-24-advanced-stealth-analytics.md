# Advanced Stealth & Analytics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Multi-Hop Chaining, QUIC protocols (Hysteria2/TUIC), and a unified analytics dashboard.

**Architecture:**
- **Master:** Recursive `ChainManager` with cycle detection. API for real-time stats aggregation.
- **Agent:** `SmartProvisioner` support for `sing-box`. New `sing-box` based providers.
- **CLI/Web:** TUI-based monitor and protected Web Dashboard for visualization.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Typer, sing-box, rich.live, Jinja2, Chart.js.

---

### Task 1: Recursive Multi-Hop Chaining (Master)

**Files:**
- Modify: `master/kosatka_master/services/chain_manager.py`
- Test: `master/tests/test_multi_hop.py`

- [ ] **Step 1: Implement full path resolver with cycle detection**
Add a recursive method to `ChainManager` that builds an ordered list of nodes from Proxy to Exit.
```python
def resolve_full_chain(self, start_node: Node) -> List[Node]:
    path = []
    visited = set()
    curr = start_node
    while curr:
        if curr.id in visited: raise CycleError()
        path.append(curr)
        visited.add(curr.id)
        if curr.role == "exit": return path
        if not curr.upstream_id: raise BrokenChainError()
        curr = fetch_node(curr.upstream_id)
```

- [ ] **Step 2: Update `provision_chain` to support N-nodes**
Iterate over the resolved path in reverse (Exit first, then Relays).

- [ ] **Step 3: Add tests for long chains (3+ nodes)**
Verify sequences of calls and error handling for cycles.

- [ ] **Step 4: Commit**
`git commit -m "feat(master): implement recursive multi-hop chain orchestration"`

---

### Task 2: Sing-box Integration & QUIC Providers (Agent)

**Files:**
- Modify: `agent/kosatka_agent/installer.py`
- Create: `agent/kosatka_agent/providers/singbox.py`

- [ ] **Step 1: Update `SmartProvisioner` for `sing-box`**
Add download logic for `sing-box` (GitHub releases).

- [ ] **Step 2: Implement `Hysteria2Provider` and `TUICProvider`**
Create a base `SingboxProvider` that manages the `sing-box` process and generates JSON configs.

- [ ] **Step 3: Integrate into `main.py`**
Allow selecting these providers via `AGENT_PROVIDER_TYPE`.

- [ ] **Step 4: Commit**
`git commit -m "feat(agent): add sing-box support and QUIC providers (Hy2/TUIC)"`

---

### Task 3: Real-time Stats Aggregator & CLI Monitor

**Files:**
- Modify: `master/kosatka_master/api/v1/stats.py`
- Modify: `cli/kosatka_cli/main.py`
- Create: `cli/kosatka_cli/monitor.py`

- [ ] **Step 1: Implement `GET /api/v1/stats/realtime` on Master**
Aggregate the latest `NodeStat` for all nodes. Ensure it returns CPU EMA and current Bandwidth.

- [ ] **Step 2: Implement CLI `monitor` command**
Use `rich.live.Live` and `rich.table.Table` to create a live dashboard.

- [ ] **Step 3: Commit**
`git commit -m "feat(cli): add real-time node monitor command"`

---

### Task 4: Protected Web Dashboard (Master)

**Files:**
- Create: `master/kosatka_master/api/v1/dashboard.py`
- Create: `master/templates/dashboard.html`

- [ ] **Step 1: Implement protected `/dashboard` route**
Verify `X-Kosatka-Key` or a simple basic-auth session.

- [ ] **Step 2: Build Jinja2 template with Chart.js**
Fetch `realtime` stats and render interactive charts.

- [ ] **Step 3: Commit**
`git commit -m "feat(master): add protected web analytics dashboard"`
