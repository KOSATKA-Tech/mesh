import asyncio
import logging

import psutil

logger = logging.getLogger("kosatka_master.host_monitor")


class HostMonitor:
    def __init__(self, cleanup_interval: int = 86400):
        self.cleanup_interval = cleanup_interval
        self._stop_event = asyncio.Event()
        self._task = None
        self._cleanup_task = None

    def get_metrics(self):
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        # Temperature (Best effort)
        temp = None
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    if entries:
                        temp = entries[0].current
                        break
        except Exception:
            pass

        return {
            "cpu_usage_percent": psutil.cpu_percent(),
            "memory_usage_percent": mem.percent,
            "disk_usage_percent": disk.percent,
            "temperature": temp,
        }

    async def cleanup(self):
        logger.info("Master host cleanup starting...")
        try:
            process = await asyncio.create_subprocess_exec(
                "docker",
                "system",
                "prune",
                "-af",
                "--volumes",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                logger.info("Master Docker cleanup successful")
            else:
                logger.warning(f"Master Docker cleanup failed: {stderr.decode()}")
        except Exception as e:
            logger.error(f"Error during Master Docker cleanup: {e}")

    async def run_periodic_cleanup(self):
        await self.cleanup()
        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.cleanup_interval)
            except asyncio.TimeoutError:
                await self.cleanup()

    def start(self):
        if self._cleanup_task is None or self._cleanup_task.done():
            self._stop_event.clear()
            self._cleanup_task = asyncio.create_task(self.run_periodic_cleanup())

    async def stop(self):
        self._stop_event.set()
        if self._cleanup_task:
            try:
                await asyncio.wait_for(self._cleanup_task, timeout=5.0)
            except asyncio.TimeoutError:
                self._cleanup_task.cancel()
