import asyncio
import logging

logger = logging.getLogger("kosatka_agent.host_manager")


class HostManager:
    def __init__(self, cleanup_interval: int = 86400):  # Default 24 hours
        self.cleanup_interval = cleanup_interval
        self._stop_event = asyncio.Event()
        self._task = None

    async def cleanup(self):
        logger.info("Starting host cleanup...")

        # 1. Docker cleanup (prune images and containers)
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
                logger.info("Docker system prune successful")
            else:
                logger.warning(f"Docker system prune failed: {stderr.decode()}")
        except Exception as e:
            logger.error(f"Error during Docker cleanup: {e}")

        # 2. /tmp cleanup (optional, be careful)
        # For now, let's just log and maybe do very basic stuff if needed.
        # Most of our data is in Docker.

        logger.info("Host cleanup complete")

    async def run(self):
        logger.info(f"HostManager background task started (interval={self.cleanup_interval}s)")
        # Run first cleanup on start
        await self.cleanup()

        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.cleanup_interval)
            except asyncio.TimeoutError:
                await self.cleanup()

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
                self._task.cancel()
