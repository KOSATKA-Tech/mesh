# Stealth Chaining & Smart Provisioning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement server chaining (Proxy -> Exit) for traffic obfuscation and autonomous "zero-touch" VPN provider installation on Agents.

**Architecture:**
- **Master:** Extended `Node` model with `role` and `upstream_id`. Orchestration logic for chained provisioning.
- **CLI:** Interactive Typer-based registration with role-aware prompts.
- **Agent:** `SmartProvisioner` for environment detection and silent binary/Docker-based installation of Xray and WireGuard-go.
- **Stealth Tunnel:** Xray with VLESS + Reality for obfuscated communication between nodes.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Typer, Xray-core, WireGuard-go, Docker API (python-on-whales or raw subprocess).

---

### Task 1: Master Model & Migration (Node Roles)

**Files:**
- Modify: `master/kosatka_master/models/node.py`
- Create: `master/alembic/versions/add_node_roles.py`

- [ ] **Step 1: Update Node model**
Add `role` (String, default='standalone') and `upstream_id` (Integer, nullable, ForeignKey('nodes.id')).
```python
# master/kosatka_master/models/node.py
class Node(Base):
    # ... existing fields
    role: Mapped[str] = mapped_column(String(50), default="standalone")
    upstream_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id"), nullable=True)
    # relationship for upstream/downstream if needed
```

- [ ] **Step 2: Generate migration**
Run: `cd master && alembic revision --autogenerate -m "add_node_roles"`

- [ ] **Step 3: Verify migration**
Run: `alembic upgrade head`

- [ ] **Step 4: Commit**
`git commit -m "feat(master): add node roles and upstream_id to model"`

---

### Task 2: Interactive CLI Registration

**Files:**
- Modify: `cli/kosatka_cli/nodes.py`
- Modify: `cli/kosatka_cli/api.py`

- [ ] **Step 1: Update API Client**
Update `register_node` to accept `role` and `upstream_id`. Update `list_nodes` to optionally filter by role (needed for exit selection).

- [ ] **Step 2: Implement interactive prompts in Typer**
```python
# cli/kosatka_cli/nodes.py
@app.command("add")
def register_node(...):
    if role is None:
        role = typer.prompt("Select node role", type=click.Choice(["standalone", "proxy", "exit"]), default="standalone")

    upstream_id = None
    if role == "proxy":
        exits = await client.list_nodes(role="exit")
        # Show table of exits and prompt for ID
        upstream_id = typer.prompt("Select upstream Exit node ID")
```

- [ ] **Step 3: Commit**
`git commit -m "feat(cli): implement interactive node registration with roles"`

---

### Task 3: Agent Smart Provisioner (Installer)

**Files:**
- Create: `agent/kosatka_agent/installer.py`
- Modify: `agent/kosatka_agent/main.py`

- [ ] **Step 1: Environment detection logic**
Implement `is_inside_docker()` and `get_system_info()` (arch, distro).

- [ ] **Step 2: Binary downloader**
Implement logic to download stashed static binaries (Xray, WireGuard-go) from GitHub releases or a mirror.

- [ ] **Step 3: Docker-based provisioning**
If Docker is present, generate a `docker-compose.sidecars.yml` and start needed services.

- [ ] **Step 4: Integrate in lifespan**
Call `provisioner.ensure_providers()` on Agent startup.

- [ ] **Step 5: Commit**
`git commit -m "feat(agent): add smart provisioner for zero-touch install"`

---

### Task 4: Stealth Chaining (Xray Reality)

**Files:**
- Create: `agent/kosatka_agent/providers/xray_relay.py`
- Modify: `agent/kosatka_agent/main.py`

- [ ] **Step 1: Implement XrayRelayProvider**
Logic to generate Xray config for `Proxy` (outbound to Exit) and `Exit` (inbound Reality server).

- [ ] **Step 2: Reality keys management**
Master generates `shortId` and `privateKey` for each Proxy-Exit pair and passes them via Agent API.

- [ ] **Step 3: Commit**
`git commit -m "feat(agent): implement xray reality chaining logic"`

---

### Task 5: Chained Provisioning Flow (Master Orchestration)

**Files:**
- Modify: `master/kosatka_master/api/v1/clients.py`
- Create: `master/kosatka_master/services/chain_manager.py`

- [ ] **Step 1: Logic for 'stealth' protocol**
If `protocol == 'stealth'`, pick a `Proxy` node. Resolve its `upstream_exit_node`.

- [ ] **Step 2: Coordinate calls**
1. Call Exit Agent: Allocate internal IP and VLESS user.
2. Call Proxy Agent: Configure relay to Exit and client inbound.

- [ ] **Step 3: Tests**
Create `master/tests/test_chain_provisioning.py` mocking both agents.

- [ ] **Step 4: Commit**
`git commit -m "feat(master): implement coordinated chained provisioning"`
