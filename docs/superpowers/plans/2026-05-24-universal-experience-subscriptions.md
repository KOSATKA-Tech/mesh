# Universal Experience & Subscriptions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform Kosatka Mesh into a subscription provider and unify on sing-box core for a seamless user experience.

**Architecture:**
- **Master:** Token-based subscription API delivering Clash/Sing-box configs.
- **Agent:** Universal `SingboxProvider` for all protocols.
- **Top-tier UI:** Intelligent naming and grouping of servers for end-users.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, PyYAML, sing-box.

---

### Task 1: Subscription Token & Client Model Update (Master)

**Files:**
- Modify: `master/kosatka_master/models/client.py`
- Create: `master/alembic/versions/add_client_sub_token.py`

- [ ] **Step 1: Update Client model**
Add `sub_token` (String, unique, index) and `sub_enabled` (Boolean, default=True). Generate a UUID token on creation.
```python
import uuid
# ...
sub_token: Mapped[str] = mapped_column(String(100), unique=True, index=True, default=lambda: str(uuid.uuid4()))
```

- [ ] **Step 2: Generate and apply migration**
`cd master && alembic revision --autogenerate -m "add_client_sub_token" && alembic upgrade head`

- [ ] **Step 3: Commit**
`git commit -m "feat(master): add subscription tokens to Client model"`

---

### Task 2: Clash YAML Generator (Master)

**Files:**
- Create: `master/kosatka_master/services/subscription_generator.py`
- Test: `master/tests/test_sub_generator.py`

- [ ] **Step 1: Implement `ClashConfigGenerator`**
Logic to convert a list of active Nodes/Chains into a valid Clash YAML.
- Groups: `🚀 Auto Select` (url-test), `🛠 Manual Select` (select).
- Proxies: VLESS, WireGuard, Hysteria2.

- [ ] **Step 2: Implement Node Naming**
Use a basic GeoIP lookup (or a placeholder dictionary if DB not ready) to add flags/names.

- [ ] **Step 3: Commit**
`git commit -m "feat(master): implement Clash YAML subscription generator"`

---

### Task 3: Subscription API Endpoint (Master)

**Files:**
- Create: `master/kosatka_master/api/v1/subscriptions.py` (or update existing)
- Modify: `master/kosatka_master/main.py`

- [ ] **Step 1: Implement `GET /sub/{token}`**
Public endpoint (no key required, authorized by token).
Returns `Content-Type: application/x-yaml` or similar.
Add headers for subscription metadata (Clash-compatible).

- [ ] **Step 2: Tests**
Verify token lookup and YAML response.

- [ ] **Step 3: Commit**
`git commit -m "feat(master): add public subscription API endpoint"`

---

### Task 4: Unified Sing-box Provider (Agent)

**Files:**
- Modify: `agent/kosatka_agent/providers/singbox.py`
- Modify: `agent/kosatka_agent/main.py`

- [ ] **Step 1: Consolidate sing-box logic**
Ensure `SingboxProvider` can handle all inbound types needed (VLESS, Hy2, TUIC) in a single instance if possible, or support clean side-by-side management.

- [ ] **Step 2: Update `get_provider` in `main.py`**
Make `sing-box` the default when requested.

- [ ] **Step 3: Commit**
`git commit -m "feat(agent): unify on sing-box as the primary transport core"`

---

### Task 5: Final Polishing & README (Master/Docs)

**Files:**
- Modify: `README.md`
- Modify: `master/templates/dashboard.html` (Add sub link)

- [ ] **Step 1: Update README**
Add sections about Subscriptions, Clash compatibility, and intelligent naming.

- [ ] **Step 2: Commit**
`git commit -m "docs: finalize Phase 4 documentation"`
