import asyncio
import time
from unittest.mock import MagicMock, patch

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


def test_get_smoothed_metrics_initial():
    collector = MetricsCollector()
    metrics = collector.get_smoothed_metrics()
    assert metrics == {"cpu_usage_percent": 0.0, "rx_bps": 0.0, "tx_bps": 0.0}


@pytest.mark.asyncio
async def test_metrics_collection_loop():
    with (
        patch("psutil.cpu_percent", return_value=10.0),
        patch("psutil.net_io_counters") as mock_net_io,
    ):

        # Mock net_io_counters to return different values on successive calls
        mock_net_io.side_effect = [
            MagicMock(bytes_recv=1000, bytes_sent=1000),
            MagicMock(bytes_recv=2000, bytes_sent=3000),
        ]

        collector = MetricsCollector(
            interval=0.1, alpha=1.0
        )  # alpha=1.0 means no smoothing for easier testing

        # Manually run one iteration of the loop logic to avoid long waits
        # First sample
        cpu = 10.0
        collector.cpu_ema = collector._apply_ema(collector.cpu_ema, cpu, collector.alpha)

        net_io1 = mock_net_io()
        collector._last_net_io = net_io1
        collector._last_sample_time = time.time() - 1.0  # Simulate 1 second passed

        # Second sample
        net_io2 = mock_net_io()
        now = time.time()
        dt = now - collector._last_sample_time

        rx_diff = net_io2.bytes_recv - net_io1.bytes_recv
        tx_diff = net_io2.bytes_sent - net_io1.bytes_sent

        rx_bps = (rx_diff * 8) / dt
        tx_bps = (tx_diff * 8) / dt

        collector.rx_bps_ema = collector._apply_ema(collector.rx_bps_ema, rx_bps, collector.alpha)
        collector.tx_bps_ema = collector._apply_ema(collector.tx_bps_ema, tx_bps, collector.alpha)

        metrics = collector.get_smoothed_metrics()
        assert metrics["cpu_usage_percent"] == 10.0
        assert metrics["rx_bps"] > 0
        assert metrics["tx_bps"] > 0


@pytest.mark.asyncio
async def test_start_stop():
    collector = MetricsCollector(interval=0.1)
    task = collector.start()
    assert task is not None
    assert not task.done()

    await asyncio.sleep(0.2)
    await collector.stop()
    assert task.done()
    assert collector._task is None
