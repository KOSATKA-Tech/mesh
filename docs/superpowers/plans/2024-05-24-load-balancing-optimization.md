# Performance Optimization Task 6: Load Balancing Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement trend-aware node scoring for better load balancing.

**Architecture:** Update `_pick_node` to calculate scores based on active client count, CPU/bandwidth trends, and saturation thresholds. Fix pruning logic in `NodeManager`.

**Tech Stack:** Python, SQLAlchemy, FastAPI.

---

### Task 1: Fix Pruning Logic in NodeManager

**Files:**
- Modify: `master/kosatka_master/services/node_manager.py`

- [ ] **Step 1: Update pruning logic**
Implement correct pruning that keeps the 20 most recent stats per node efficiently.

### Task 2: Implement Trend-Aware Scoring in _pick_node

**Files:**
- Modify: `master/kosatka_master/api/v1/clients.py`

- [ ] **Step 1: Update _pick_node logic**
Implement the scoring algorithm in `_pick_node`:
- Fetch all active nodes for protocol.
- Count active clients on each node.
- Fetch last 5 stats for each node.
- Calculate trend penalties (CPU/RX increasing).
- Calculate saturation penalties (CPU > 70%, RX > 80%).
- Pick the node with the lowest score.

### Task 3: Verification

**Files:**
- Create: `master/tests/test_load_balancer.py`

- [ ] **Step 1: Write tests for scoring logic**
Verify the load balancer correctly penalizes nodes with rising load or high saturation.

- [ ] **Step 2: Run tests**
Run: `uv run pytest master/tests/test_load_balancer.py`
Expected: PASS
