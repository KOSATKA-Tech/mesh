import asyncio
import logging
import time
from typing import Any, Dict

from .metrics import MetricsCollector
from .providers.base import BaseAgentProvider
from .shaper import TrafficShaper

logger = logging.getLogger("kosatka_agent.protector")


class HeavyweightProtector:
    def __init__(
        self,
        shaper: TrafficShaper,
        provider: BaseAgentProvider,
        metrics_collector: MetricsCollector,
        interval: int = 10,
        penalty_duration: int = 120,
        cpu_threshold: float = 70.0,
        bw_threshold_ratio: float = 0.8,
        total_bw_bps: float = 1_000_000_000,  # 1gbit default
    ):
        self.shaper = shaper
        self.provider = provider
        self.metrics_collector = metrics_collector
        self.interval = interval
        self.penalty_duration = penalty_duration
        self.cpu_threshold = cpu_threshold
        self.bw_threshold = total_bw_bps * bw_threshold_ratio

        self.penalty_box: Dict[str, float] = {}  # ip: expiry_time
        self._last_stats: Dict[str, Dict[str, Any]] = {}  # client_id: stats
        self._last_stats_time: float = 0
        self._stop_event = asyncio.Event()
        self._task = None

    async def run(self):
        logger.info("HeavyweightProtector started")
        while not self._stop_event.is_set():
            try:
                await self._process_cycle()
            except Exception as e:
                logger.error(f"Error in protector cycle: {e}")

            try:
                # Use wait with timeout to allow immediate stop
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval)
            except asyncio.TimeoutError:
                pass

    async def _process_cycle(self):
        now = time.time()

        # 1. Cleanup expired penalties
        expired = [ip for ip, expiry in self.penalty_box.items() if now > expiry]
        for ip in expired:
            logger.info(f"Penalty expired for {ip}, removing throttle")
            await self.shaper.remove_throttle(ip)
            del self.penalty_box[ip]

        # 2. Check system load
        metrics = self.metrics_collector.get_smoothed_metrics()
        cpu_load = metrics.get("cpu_usage_percent", 0)
        rx_load = metrics.get("rx_bps", 0)

        high_load = cpu_load > self.cpu_threshold or rx_load > self.bw_threshold

        # 3. Collect client stats
        clients = await self.provider.get_clients()
        current_stats = {}
        for client in clients:
            client_id = client["client_id"]
            stats = await self.provider.get_client_stats(client_id)
            current_stats[client_id] = {"stats": stats, "address": client["address"].split("/")[0]}

        if self._last_stats and high_load:
            # 4. Identify heavy hitters
            dt = now - self._last_stats_time
            heavy_hitters = []

            for client_id, data in current_stats.items():
                if client_id in self._last_stats:
                    last_rx = self._last_stats[client_id]["stats"].get("transfer_rx", 0)
                    curr_rx = data["stats"].get("transfer_rx", 0)
                    bw = ((curr_rx - last_rx) * 8) / dt if dt > 0 else 0
                    heavy_hitters.append({"ip": data["address"], "bw": bw})

            # Sort by BW descending
            heavy_hitters.sort(key=lambda x: x["bw"], reverse=True)

            # Throttle top 3 (if they are actually using BW)
            for hitter in heavy_hitters[:3]:
                if hitter["bw"] > 1_000_000:  # at least 1Mbps
                    ip = hitter["ip"]
                    if ip not in self.penalty_box:
                        logger.warning(
                            f"High load detected! Throttling heavy hitter: {ip} ({hitter['bw'] / 1e6:.2f} Mbps)"
                        )
                        await self.shaper.apply_throttle(ip, rate_kbps=5000)
                        self.penalty_box[ip] = now + self.penalty_duration

        self._last_stats = current_stats
        self._last_stats_time = now

    def start(self):
        if self._task is None or self._task.done():
            self._stop_event.clear()
            self._task = asyncio.create_task(self.run())

    async def stop(self):
        if self._task:
            self._stop_event.set()
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("HeavyweightProtector task did not stop in time, cancelling")
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            self._task = None
