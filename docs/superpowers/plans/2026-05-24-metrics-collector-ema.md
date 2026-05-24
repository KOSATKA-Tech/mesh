# Metric Collector with EMA Smoothing (Agent) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a background service that samples CPU and Network metrics and smooths them using Exponential Moving Average (EMA).

**Architecture:**
- `MetricsCollector` class in `agent/kosatka_agent/metrics.py`.
- Background task using `asyncio` to sample metrics every 10 seconds.
- CPU usage and Network I/O (rx/tx bytes) sampling.
- EMA smoothing with `alpha=0.3`.
- Integration into `lifespan` in `agent/kosatka_agent/main.py`.
- Health check endpoint update.

**Tech Stack:**
- Python 3.10+
- `psutil`
- `FastAPI`
- `asyncio`

---

### Task 1: Add psutil dependency

**Files:**
- Modify: `agent/pyproject.toml`

- [ ] **Step 1: Add psutil to dependencies**

```toml
dependencies = [
    "fastapi",
    "uvicorn",
    "pydantic",
    "pydantic-settings",
    "httpx",
    "python-multipart",
    "psutil",
]
```

- [ ] **Step 2: Commit**

```bash
git add agent/pyproject.toml
git commit -m "chore: add psutil dependency"
```

### Task 2: Implement MetricsCollector (Red-Green-Refactor)

**Files:**
- Create: `agent/kosatka_agent/metrics.py`
- Create: `agent/tests/test_metrics.py`

- [ ] **Step 1: Write failing test for MetricsCollector EMA logic**

```python
import pytest
from kosatka_agent.metrics import MetricsCollector

def test_ema_smoothing():
    collector = MetricsCollector()
    alpha = 0.3

    # First value should set the initial state
    v1 = 10.0
    ema1 = collector._apply_ema(None, v1, alpha)
    assert ema1 == v1

    # Second value should be smoothed
    v2 = 20.0
    ema2 = collector._apply_ema(v1, v2, alpha)
    # ema = 0.3 * 20 + 0.7 * 10 = 6 + 7 = 13
    assert ema2 == 13.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest agent/tests/test_metrics.py -v`
Expected: FAIL (ModuleNotFoundError or ImportError)

- [ ] **Step 3: Implement minimal MetricsCollector with EMA logic**

```python
import asyncio
import logging
import time
import psutil

logger = logging.getLogger("kosatka_agent.metrics")

class MetricsCollector:
    def __init__(self, interval: int = 10, alpha: float = 0.3):
        self.interval = interval
        self.alpha = alpha
        self.cpu_ema = None
        self.rx_bps_ema = None
        self.tx_bps_ema = None

        self._last_net_io = None
        self._last_sample_time = None
        self._stop_event = asyncio.Event()
        self._task = None

    def _apply_ema(self, prev_ema, current_value, alpha):
        if prev_ema is None:
            return current_value
        return alpha * current_value + (1 - alpha) * prev_ema

    def get_smoothed_metrics(self):
        return {
            "cpu_usage_percent": round(self.cpu_ema, 2) if self.cpu_ema is not None else 0,
            "rx_bps": round(self.rx_bps_ema, 2) if self.rx_bps_ema is not None else 0,
            "tx_bps": round(self.tx_bps_ema, 2) if self.tx_bps_ema is not None else 0,
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest agent/tests/test_metrics.py -v`
Expected: PASS

- [ ] **Step 5: Write test for background sampling**

```python
@pytest.mark.asyncio
async def test_metrics_collection_loop(mocker):
    # Mock psutil
    mock_cpu = mocker.patch("psutil.cpu_percent", return_value=10.0)
    mock_net = mocker.patch("psutil.net_io_counters", return_value=mocker.Mock(bytes_recv=1000, bytes_sent=1000))

    collector = MetricsCollector(interval=0.1)
    await collector.start()
    await asyncio.sleep(0.25) # Allow at least 2 samples
    await collector.stop()

    metrics = collector.get_smoothed_metrics()
    assert metrics["cpu_usage_percent"] == 10.0
    assert mock_cpu.call_count >= 2
```

- [ ] **Step 6: Complete MetricsCollector implementation**

```python
    async def start(self):
        if self._task is not None:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())
        logger.info("Metrics collector started")

    async def stop(self):
        if self._task is None:
            return
        self._stop_event.set()
        await self._task
        self._task = None
        logger.info("Metrics collector stopped")

    async def _run(self):
        while not self._stop_event.is_set():
            try:
                self._sample()
            except Exception as e:
                logger.error(f"Error sampling metrics: {e}")

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval)
            except asyncio.TimeoutError:
                pass

    def _sample(self):
        now = time.time()
        cpu = psutil.cpu_percent()
        net_io = psutil.net_io_counters()

        self.cpu_ema = self._apply_ema(self.cpu_ema, cpu, self.alpha)

        if self._last_net_io is not None and self._last_sample_time is not None:
            dt = now - self._last_sample_time
            if dt > 0:
                rx_diff = net_io.bytes_recv - self._last_net_io.bytes_recv
                tx_diff = net_io.bytes_sent - self._last_net_io.bytes_sent

                # Convert to bits per second
                rx_bps = (rx_diff * 8) / dt
                tx_bps = (tx_diff * 8) / dt

                self.rx_bps_ema = self._apply_ema(self.rx_bps_ema, rx_bps, self.alpha)
                self.tx_bps_ema = self._apply_ema(self.tx_bps_ema, tx_bps, self.alpha)

        self._last_net_io = net_io
        self._last_sample_time = now
```

- [ ] **Step 7: Run all metrics tests**

Run: `pytest agent/tests/test_metrics.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add agent/kosatka_agent/metrics.py agent/tests/test_metrics.py
git commit -m "feat: implement MetricsCollector with EMA smoothing"
```

### Task 3: Integrate into main.py

**Files:**
- Modify: `agent/kosatka_agent/main.py`

- [ ] **Step 1: Import MetricsCollector and initialize**

```python
from .metrics import MetricsCollector

metrics_collector = MetricsCollector()
```

- [ ] **Step 2: Update lifespan to start/stop collector**

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    await metrics_collector.start()
    # ... existing bootstrap logic ...
    yield
    # Shutdown logic
    await metrics_collector.stop()
    logger.info("Kosatka Agent shutting down")
```

- [ ] **Step 3: Update health endpoint**

```python
@app.get("/health/")
async def health():
    return {
        "status": "ok",
        "provider": settings.provider_type,
        "metrics": metrics_collector.get_smoothed_metrics()
    }
```

- [ ] **Step 4: Commit**

```bash
git add agent/kosatka_agent/main.py
git commit -m "feat: integrate MetricsCollector into agent lifespan and health endpoint"
```

### Task 4: Integration Test

**Files:**
- Create: `agent/tests/test_health_metrics.py`

- [ ] **Step 1: Write test for health endpoint metrics**

```python
from fastapi.testclient import TestClient
from kosatka_agent.main import app
import pytest

def test_health_endpoint_contains_metrics():
    client = TestClient(app)
    response = client.get("/health/")
    assert response.status_code == 200
    data = response.json()
    assert "metrics" in data
    assert "cpu_usage_percent" in data["metrics"]
    assert "rx_bps" in data["metrics"]
    assert "tx_bps" in data["metrics"]
```

- [ ] **Step 2: Run integration test**

Run: `pytest agent/tests/test_health_metrics.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add agent/tests/test_health_metrics.py
git commit -m "test: verify health endpoint returns metrics"
```

---
