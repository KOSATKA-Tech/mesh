# Real-time Stats Aggregator & CLI Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a real-time monitoring system for the mesh with a Master API endpoint and a CLI live monitor.

**Architecture:**
- **Master API**: Add `GET /api/v1/stats/realtime` to aggregate the 5 most recent `NodeStat` entries for all active nodes.
- **CLI API**: Add `get_realtime_stats()` to `APIClient`.
- **CLI Monitor**: Create a `monitor` command using `rich.live.Live` to display a live-updating table of node stats.

**Tech Stack:** FastAPI, SQLAlchemy, Typer, Rich (Live, Table, Sparkline-like values).

---

### Task 1: Implement Master API Endpoint

**Files:**
- Modify: `master/kosatka_master/api/v1/stats.py`
- Test: `master/tests/test_stats_api.py`

- [ ] **Step 1: Write the failing test for realtime stats**

```python
import pytest
from httpx import AsyncClient
from kosatka_master.models.node import Node, NodeStat

@pytest.mark.asyncio
async def test_get_realtime_stats(client: AsyncClient, db_session):
    # Create a node
    node = Node(name="test-node", address="1.1.1.1", provider_type="agent", is_active=True)
    db_session.add(node)
    await db_session.commit()

    # Create some stats
    for i in range(3):
        stat = NodeStat(node_id=node.id, cpu_ema=10.0 + i, rx_bps=100.0, tx_bps=200.0)
        db_session.add(stat)
    await db_session.commit()

    response = await client.get("/api/v1/stats/realtime", headers={"X-Kosatka-Key": "admin-key"})
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert len(data["nodes"]) > 0
    assert data["nodes"][0]["name"] == "test-node"
    assert len(data["nodes"][0]["cpu_history"]) == 3
```

- [ ] **Step 2: Implement the endpoint in `master/kosatka_master/api/v1/stats.py`**

```python
from sqlalchemy.orm import selectinload

@router.get("/realtime")
async def get_realtime_stats(db: AsyncSession = Depends(get_db)):
    # Query active nodes and their 5 most recent stats
    # Using a subquery or window function might be complex for 5 per node in a single query with SQLAlchemy easily,
    # so we'll do it efficiently with selectinload and then slice or use a more advanced query.
    # For now, let's get all active nodes and their stats ordered by timestamp desc.

    stmt = (
        select(Node)
        .where(Node.is_active == True)
        .options(
            selectinload(Node.stats)
        )
    )
    result = await db.execute(stmt)
    nodes = result.scalars().all()

    nodes_stats = []
    for node in nodes:
        # Get 5 most recent stats
        recent_stats = sorted(node.stats, key=lambda s: s.timestamp, reverse=True)[:5]
        nodes_stats.append({
            "id": node.id,
            "name": node.name,
            "cpu_history": [s.cpu_ema for s in reversed(recent_stats)],
            "rx_history": [s.rx_bps for s in reversed(recent_stats)],
            "tx_history": [s.tx_bps for s in reversed(recent_stats)],
            "status": node.status
        })

    return {"nodes": nodes_stats}
```

- [ ] **Step 3: Run tests and verify**

- [ ] **Step 4: Commit**

### Task 2: Update CLI API Client

**Files:**
- Modify: `cli/kosatka_cli/api.py`

- [ ] **Step 1: Add `get_realtime_stats` method to `APIClient`**

```python
    async def get_realtime_stats(self) -> Dict[str, Any]:
        return await self.request("GET", "/stats/realtime")
```

### Task 3: Implement CLI Monitor Command

**Files:**
- Create: `cli/kosatka_cli/monitor.py`
- Modify: `cli/kosatka_cli/main.py`
- Test: `cli/tests/test_monitor.py`

- [ ] **Step 1: Implement `cli/kosatka_cli/monitor.py`**

```python
import asyncio
import typer
from rich.live import Live
from rich.table import Table
from rich.console import Console
from .api import APIClient

app = typer.Typer()
console = Console()

def generate_table(stats_data):
    table = Table(title="Mesh Real-time Monitor")
    table.add_column("Node ID", justify="right", style="cyan", no_wrap=True)
    table.add_column("Name", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("CPU % (last 5)", justify="center")
    table.add_column("RX (bps)", justify="right")
    table.add_column("TX (bps)", justify="right")

    for node in stats_data.get("nodes", []):
        cpu_history = node.get("cpu_history", [])
        cpu_str = " ".join([f"{v:.1f}" for v in cpu_history])

        last_rx = node.get("rx_history", [-1])[-1]
        last_tx = node.get("tx_history", [-1])[-1]

        rx_str = f"{last_rx:,.0f}" if last_rx >= 0 else "N/A"
        tx_str = f"{last_tx:,.0f}" if last_tx >= 0 else "N/A"

        table.add_row(
            str(node["id"]),
            node["name"],
            node["status"],
            cpu_str,
            rx_str,
            tx_str
        )
    return table

async def monitor_loop():
    api = APIClient()
    with Live(generate_table({}), refresh_per_second=1, console=console) as live:
        while True:
            try:
                stats = await api.get_realtime_stats()
                live.update(generate_table(stats))
            except Exception as e:
                # Silently wait or show error in table?
                pass
            await asyncio.sleep(2)

@app.command("show")
def show():
    """Start real-time monitoring of the mesh"""
    try:
        asyncio.run(monitor_loop())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    app()
```

- [ ] **Step 2: Register the monitor command in `cli/kosatka_cli/main.py`**

```python
from . import monitor
app.add_typer(monitor.app, name="monitor")
```

- [ ] **Step 3: Add a basic test for the CLI command**

```python
import pytest
from unittest.mock import AsyncMock, patch
from kosatka_cli.monitor import monitor_loop

@pytest.mark.asyncio
async def test_monitor_loop_iteration():
    # Mock APIClient
    mock_stats = {
        "nodes": [
            {"id": 1, "name": "n1", "status": "online", "cpu_history": [1.0, 2.0], "rx_history": [100], "tx_history": [200]}
        ]
    }

    with patch("kosatka_cli.monitor.APIClient") as mock_api_class:
        mock_api = mock_api_class.return_value
        mock_api.get_realtime_stats = AsyncMock(return_value=mock_stats)

        # We need to break the loop after one iteration for testing
        with patch("asyncio.sleep", side_effect=KeyboardInterrupt):
            try:
                await monitor_loop()
            except KeyboardInterrupt:
                pass

        mock_api.get_realtime_stats.assert_called()
```

- [ ] **Step 4: Run tests and verify**

- [ ] **Step 5: Commit**
