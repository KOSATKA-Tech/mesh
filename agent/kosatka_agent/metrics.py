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
        # Memory
        mem = psutil.virtual_memory()
        # Disk
        disk = psutil.disk_usage("/")

        # Temperature (Best effort)
        temp = None
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                # Use first available core temp or package temp
                for name, entries in temps.items():
                    if entries:
                        temp = entries[0].current
                        break
        except Exception:
            pass

        return {
            "cpu_usage_percent": round(self.cpu_ema, 2) if self.cpu_ema is not None else 0.0,
            "memory_usage_percent": mem.percent,
            "disk_usage_percent": disk.percent,
            "temperature": temp,
            "rx_bps": round(self.rx_bps_ema, 2) if self.rx_bps_ema is not None else 0.0,
            "tx_bps": round(self.tx_bps_ema, 2) if self.tx_bps_ema is not None else 0.0,
        }

    async def run(self):
        logger.info(f"MetricsCollector started with interval={self.interval}s")
        while not self._stop_event.is_set():
            try:
                # CPU sample (non-blocking with 0.1s interval for more accuracy if needed,
                # but psutil.cpu_percent() with default 0.0 is also fine since we run in a loop)
                cpu = psutil.cpu_percent()
                self.cpu_ema = self._apply_ema(self.cpu_ema, cpu, self.alpha)

                # BW sample
                net_io = psutil.net_io_counters()
                now = time.time()

                if self._last_net_io is not None:
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

            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")

            try:
                # Use wait with timeout to allow immediate stop
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval)
            except asyncio.TimeoutError:
                pass

    def start(self):
        if self._task is None or self._task.done():
            self._stop_event.clear()
            self._task = asyncio.create_task(self.run())
            return self._task

    async def stop(self):
        if self._task:
            self._stop_event.set()
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("MetricsCollector task did not stop in time, cancelling")
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            self._task = None
