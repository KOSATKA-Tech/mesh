import asyncio
import logging

logger = logging.getLogger("kosatka_agent.shaper")


class TrafficShaper:
    def __init__(self, interface: str, total_rate: str):
        self.interface = interface
        self.total_rate = total_rate
        self.throttled_class_id = "1:10"
        self.priority_class_id = "1:1"

    async def _run_tc(self, *args):
        cmd = ["tc"] + list(args)
        logger.debug(f"Running command: {' '.join(cmd)}")
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                logger.error(f"tc command failed: {' '.join(cmd)}")
                logger.error(f"stderr: {stderr.decode()}")
                return False
            return True
        except Exception as e:
            logger.error(f"Failed to execute tc: {e}")
            return False

    async def setup_shaping(self):
        """Initialize HTB qdisc and classes."""
        logger.info(f"Setting up traffic shaping on {self.interface} with rate {self.total_rate}")

        # Cleanup first just in case
        await self.cleanup_shaping()

        # 1. Add HTB qdisc to root. Default traffic goes to 1:1.
        await self._run_tc(
            "qdisc", "add", "dev", self.interface, "root", "handle", "1:", "htb", "default", "1"
        )

        # 2. Add root class with total rate
        await self._run_tc(
            "class",
            "add",
            "dev",
            self.interface,
            "parent",
            "1:",
            "classid",
            "1:1",
            "htb",
            "rate",
            self.total_rate,
            "burst",
            "15k",
        )

        # 3. Add throttled class (placeholder, will be updated per IP if needed or used as a template)
        # Actually we need at least one throttled class defined.
        # Let's define 1:10 as a class that we'll move IPs into.
        # We'll use a very high rate by default for 1:10 and then use filters to throttle.
        # Wait, HTB works by classes. To have different rates for different IPs,
        # we either need many classes or one class that we move IPs into.
        # If we move multiple IPs into 1:10, they SHARE the rate of 1:10.
        # Task 4 goal: "1:10 - Throttled (For heavy hitters)".
        # This implies a shared bucket for heavy hitters.
        # The user might want individual throttling later, but for now 1:10 is "Throttled".

        # Default rate for throttled class if not specified.
        await self._run_tc(
            "class",
            "add",
            "dev",
            self.interface,
            "parent",
            "1:1",
            "classid",
            "1:10",
            "htb",
            "rate",
            "1mbit",
            "ceil",
            "1mbit",
            "burst",
            "15k",
        )

    async def cleanup_shaping(self):
        """Remove HTB qdisc."""
        logger.info(f"Cleaning up traffic shaping on {self.interface}")
        await self._run_tc("qdisc", "del", "dev", self.interface, "root")

    async def apply_throttle(self, ip: str, rate_kbps: int):
        """
        Move an IP to the Throttled class.
        Currently updates the rate for the whole Throttled class.
        """
        logger.info(f"Throttling IP {ip} to {rate_kbps}kbps on {self.interface}")

        # 1. Update the throttled class rate (shared by all throttled IPs)
        rate_str = f"{rate_kbps}kbit"
        await self._run_tc(
            "class",
            "change",
            "dev",
            self.interface,
            "parent",
            "1:1",
            "classid",
            "1:10",
            "htb",
            "rate",
            rate_str,
            "ceil",
            rate_str,
            "burst",
            "15k",
        )

        # 2. Add filter for this IP. Use prio 1 so it matches before default.
        # We use u32 match on dst IP because we are shaping downlink to the client.
        await self._run_tc(
            "filter",
            "add",
            "dev",
            self.interface,
            "protocol",
            "ip",
            "parent",
            "1:0",
            "prio",
            "1",
            "u32",
            "match",
            "ip",
            "dst",
            f"{ip}/32",
            "flowid",
            "1:10",
        )

    async def remove_throttle(self, ip: str):
        """Remove the throttle filter for an IP."""
        logger.info(f"Removing throttle for IP {ip} on {self.interface}")
        # To delete a filter exactly, we need to match the parameters used to create it.
        await self._run_tc(
            "filter",
            "del",
            "dev",
            self.interface,
            "protocol",
            "ip",
            "parent",
            "1:0",
            "prio",
            "1",
            "u32",
            "match",
            "ip",
            "dst",
            f"{ip}/32",
            "flowid",
            "1:10",
        )
