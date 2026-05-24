# TC HTB Engine & Shaping Logic (Agent) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a `TrafficShaper` class to manage Linux Traffic Control (tc) settings on the VPN interface for bandwidth shaping.

**Architecture:**
- `TrafficShaper` class in `agent/kosatka_agent/shaper.py`.
- Uses `asyncio.create_subprocess_exec` to run `tc`.
- Manages an HTB qdisc with a priority class (default) and a throttled class.
- Integration in `main.py` via `lifespan` hook.
- Configuration in `config.py` (enable flag, interface name, default rates).

**Tech Stack:**
- Python 3.12
- FastAPI (for lifespan)
- Pydantic Settings
- Linux `tc` (Traffic Control)

---

### Task 1: Configuration

**Files:**
- Modify: `agent/kosatka_agent/config.py`

- [ ] **Step 1: Add shaping settings to `Settings` class**

```python
    # Shaping settings
    shaping_enabled: bool = False
    shaping_total_rate: str = "1gbit"  # Total interface bandwidth
```

- [ ] **Step 2: Commit configuration changes**

```bash
git add agent/kosatka_agent/config.py
git commit -m "config: add shaping settings"
```

### Task 2: Implement TrafficShaper (TDD)

**Files:**
- Create: `agent/kosatka_agent/shaper.py`
- Create: `agent/tests/test_shaper.py`

- [ ] **Step 1: Write failing test for `TrafficShaper.setup_shaping`**

```python
import pytest
from unittest.mock import AsyncMock, patch
from kosatka_agent.shaper import TrafficShaper

@pytest.mark.asyncio
async def test_setup_shaping():
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_exec.return_value = mock_process

        shaper = TrafficShaper("wg0", "1gbit")
        await shaper.setup_shaping()

        # Verify tc commands
        assert mock_exec.call_count >= 2
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest agent/tests/test_shaper.py`

- [ ] **Step 3: Implement `TrafficShaper` class and `setup_shaping`**
Include error handling for `tc` commands.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest agent/tests/test_shaper.py`

- [ ] **Step 5: Write failing test for `apply_throttle` and `remove_throttle`**

- [ ] **Step 6: Implement `apply_throttle` and `remove_throttle`**
Ensure it uses `dst` IP for shaping (downlink to client).

- [ ] **Step 7: Implement `cleanup_shaping`**

- [ ] **Step 8: Final verification of `TrafficShaper` with tests**

- [ ] **Step 9: Commit shaper implementation**

### Task 3: Integration

**Files:**
- Modify: `agent/kosatka_agent/main.py`

- [ ] **Step 1: Initialize and cleanup `TrafficShaper` in `lifespan`**

- [ ] **Step 2: Commit integration changes**

### Task 4: Verification

- [ ] **Step 1: Run all agent tests**
Run: `pytest agent/tests/`
