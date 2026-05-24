# Design Spec: Kosatka Mesh Performance & Scalability Optimization

**Date:** 2026-05-24
**Status:** Draft
**Goal:** Enhance the performance of the Master node and implement autonomous dynamic traffic shaping on Agents to support low-end VPS deployments.

---

## 1. Problem Statement
Current limitations in Kosatka Mesh:
- **Master-Agent Communication:** High overhead due to per-request `httpx.AsyncClient` instantiation.
- **Node Selection:** Naive balancing (first available active node) leads to uneven load distribution.
- **Agent Stability:** Low-end VPS nodes (512MB-1GB RAM) are vulnerable to network/CPU saturation by single high-bandwidth users.
- **Database Management:** Lack of formal migrations (Alembic) hinders schema evolution.

## 2. Proposed Architecture

### 2.1. Master Node Enhancements
- **Alembic Integration:** Implement full database migration history.
- **Connection Pooling:** Use a singleton `httpx.AsyncClient` with HTTP/2 support for all Agent communications.
- **Advanced Load Balancing:**
    - Store real-time metrics (`load_avg`, `bandwidth_util`, `active_clients`) in the `nodes` table.
    - Implement a `node_stats` table to store a rolling window (~20 samples) of metrics.
    - **Strategy:** "Least Loaded with Trend Awareness" – prioritize nodes with low current load and stable/decreasing utilization trends.

### 2.2. Autonomous "Smart" Agent
- **Metric Collector:**
    - Background task sampling CPU (Load Average) and Network I/O every 10s.
    - **Smoothing:** Use Exponential Moving Average (EMA) and "3-of-5" rule to ignore transient CPU spikes.
- **Traffic Shaping Engine (TC HTB):**
    - Root HTB discipline on the VPN interface (e.g., `wg0`).
    - Two primary classes: `Priority` (default) and `Throttled` (limited bandwidth).
- **Heavyweight Detection (Dynamic Rate-Limiting):**
    - If sustained load > 70%, identify top-N peers by bandwidth consumption (ΔBytes/ΔTime).
    - Automatically move "Heavy Hitters" to the `Throttled` class via `tc filter`.
- **Penalty Box:**
    - Peers moved to `Throttled` remain there for a cooling period (2-5 minutes) even if server load drops, preventing oscillation.

## 3. Implementation Details

### 3.1. Agent Logic (Python/Linux)
- Use `psutil` or `/proc` for metric gathering.
- Wrap `tc` commands for class and filter management.
- State management for the "Penalty Box" using an internal async queue.

### 3.2. Master Logic (FastAPI/SQLAlchemy)
- Update `NodeManager.sync_all_nodes` to accept and persist rich metrics from Agents.
- Refactor `_pick_node` to use a scoring algorithm based on both client count and physical resource utilization trends.

## 4. Success Criteria
- Master can handle 100+ agents with minimal latency increase.
- Agents on 1-CPU nodes remain responsive (SSH/API) during high-traffic VPN usage.
- "Interactive" traffic (web browsing) for most users is preserved when a single user saturates the node's uplink.

## 5. Testing Plan
- **Load Testing:** Simulate high bandwidth usage on a throttled CPU environment to verify "Heavyweight Detection".
- **Migration Testing:** Verify Alembic can transition existing SQLite/Postgres schemas.
- **Stress Testing:** Verify Master node connection pooling behavior under high Agent counts.
