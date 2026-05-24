# Design Spec: Advanced Stealth & Analytics (Phase 3)

**Date:** 2026-05-24
**Status:** Approved
**Goal:** Implement Multi-Hop Chaining, support for QUIC-based protocols (Hysteria2/TUIC), and a unified analytics dashboard.

---

## 1. Multi-Hop Chaining
Extend the current Proxy-Exit mechanism to support chains of arbitrary length.

### 1.1. Recursive Topology
- **Linkage:** Nodes continue to use `upstream_id`.
- **Validation:**
    - A chain is valid ONLY if it terminates at a node with `role="exit"`.
    - Detect and prevent circular references during registration and provisioning.
- **Orchestration:** Master recursively resolves the full path from the starting Proxy to the final Exit. It then provisions each node in sequence.

---

## 2. QUIC-based Protocols (Hysteria2 & TUIC)
Introduce modern, high-performance UDP protocols to handle packet loss and high latency.

### 2.1. Sing-box Integration
- **SmartProvisioner:** Add `sing-box` to the list of managed binaries. Support auto-download for `x86_64` and `arm64`.
- **Providers:**
    - `Hysteria2Provider`: Implementation using `sing-box` core.
    - `TUICProvider`: Implementation using `sing-box` core.
- **Stealth:** Use `sing-box` for internal multi-hop relaying where performance is critical.

---

## 3. Unified Analytics Dashboard
Real-time monitoring of the entire mesh.

### 3.1. Master API
- **Endpoint:** `GET /api/v1/stats/realtime`.
- **Logic:** Aggregates the latest `NodeStat` entries for all active nodes.
- **Security:** Access restricted by `X-Kosatka-Key` or session cookie.

### 3.2. CLI Monitor (TUI)
- **Command:** `kosatka-mesh monitor`.
- **Implementation:** Uses `rich.live` to show live-updating sparklines and tables of CPU/Bandwidth usage across the mesh.

### 3.3. Web Dashboard
- **Endpoint:** `GET /dashboard`.
- **Implementation:** Simple, protected HTML page using Jinja2 and Chart.js for historical and real-time visualization.

---

## 4. Implementation Steps
1. **Master:** Implement recursive chain resolver and cycle detection.
2. **Agent:** Update `SmartProvisioner` for `sing-box`. Implement `Hysteria2` and `TUIC` providers.
3. **Master:** Build real-time stats aggregator.
4. **CLI:** Implement the `monitor` command with TUI.
5. **Web:** Implement the protected `/dashboard` view.

---

## 5. Testing Plan
- **Topology Tests:** Verify cycle detection and dangling chain rejection.
- **Multi-Hop Tests:** Mock a 3-node chain and verify the sequence of API calls.
- **Provider Tests:** Verify `sing-box` config generation for Hy2/TUIC.
- **Security Tests:** Ensure the dashboard is unreachable without the correct API key.
