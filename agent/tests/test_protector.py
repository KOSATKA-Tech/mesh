import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from kosatka_agent.protector import HeavyweightProtector


@pytest.mark.asyncio
async def test_protector_throttles_heavy_hitter():
    shaper = AsyncMock()
    provider = AsyncMock()
    metrics = MagicMock()

    # Mock high load
    metrics.get_smoothed_metrics.return_value = {
        "cpu_usage_percent": 80.0,
        "rx_bps": 100_000_000,
        "tx_bps": 10_000_000,
    }

    # Mock clients
    provider.get_clients.return_value = [{"client_id": "c1", "address": "10.8.0.2/32"}]

    # First call - baseline
    provider.get_client_stats.return_value = {"transfer_rx": 1000, "transfer_tx": 0}

    protector = HeavyweightProtector(shaper, provider, metrics, interval=0.1)

    # Run one cycle manually to set baseline
    await protector._process_cycle()

    # Mock heavy BW in second cycle
    # 2MB over small dt should be > 1Mbps
    provider.get_client_stats.return_value = {"transfer_rx": 2_000_000, "transfer_tx": 0}

    # Run second cycle
    await protector._process_cycle()

    # Verify throttle applied
    shaper.apply_throttle.assert_called_with("10.8.0.2", rate_kbps=5000)
    assert "10.8.0.2" in protector.penalty_box


@pytest.mark.asyncio
async def test_protector_removes_expired_penalty():
    shaper = AsyncMock()
    provider = AsyncMock()
    metrics = MagicMock()

    protector = HeavyweightProtector(shaper, provider, metrics, penalty_duration=0)
    protector.penalty_box["10.8.0.2"] = time.time() - 1

    # Mock low load to avoid new throttles
    metrics.get_smoothed_metrics.return_value = {
        "cpu_usage_percent": 10.0,
        "rx_bps": 1000,
        "tx_bps": 1000,
    }
    provider.get_clients.return_value = []

    await protector._process_cycle()

    shaper.remove_throttle.assert_called_with("10.8.0.2")
    assert "10.8.0.2" not in protector.penalty_box


@pytest.mark.asyncio
async def test_protector_no_throttle_on_low_load():
    shaper = AsyncMock()
    provider = AsyncMock()
    metrics = MagicMock()

    # Mock low load
    metrics.get_smoothed_metrics.return_value = {
        "cpu_usage_percent": 10.0,
        "rx_bps": 1000,
        "tx_bps": 1000,
    }

    # Mock clients
    provider.get_clients.return_value = [{"client_id": "c1", "address": "10.8.0.2/32"}]

    # First call - baseline
    provider.get_client_stats.return_value = {"transfer_rx": 1000, "transfer_tx": 0}

    protector = HeavyweightProtector(shaper, provider, metrics, interval=0.1)

    # Run one cycle manually to set baseline
    await protector._process_cycle()

    # Mock heavy BW in second cycle
    provider.get_client_stats.return_value = {"transfer_rx": 2_000_000, "transfer_tx": 0}

    # Run second cycle
    await protector._process_cycle()

    # Verify throttle NOT applied
    shaper.apply_throttle.assert_not_called()
    assert "10.8.0.2" not in protector.penalty_box
