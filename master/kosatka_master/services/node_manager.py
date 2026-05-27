import asyncio
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..http_client import get_global_httpx_client
from ..models.node import Node, NodeStat
from .providers.agent_provider import AgentNodeProvider


class NodeManager:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_node(
        self, name: str, address: str, provider_type: str = "agent", api_key: str | None = None
    ):
        node = Node(name=name, address=address, provider_type=provider_type, api_key=api_key)
        self.db.add(node)
        await self.db.commit()
        await self.db.refresh(node)
        return node

    async def sync_all_nodes(self):
        result = await self.db.execute(select(Node).where(Node.is_active.is_(True)))
        nodes = result.scalars().all()
        if not nodes:
            return

        # Probe every active node concurrently. The previous serial loop
        # multiplied the worst-case sync latency by N — with default
        # ``KOSATKA_SYNC_INTERVAL=60`` and a single dead node taking 5s
        # to time out, ten nodes alone could blow past the next tick and
        # starve the scheduler. ``return_exceptions=True`` keeps one
        # misbehaving agent from short-circuiting the rest.
        client = await get_global_httpx_client()

        async def _probe(node: Node) -> Dict[str, Any] | None:
            key = node.api_key or settings.effective_agent_api_key()
            provider = AgentNodeProvider(key, client=client)
            return await provider.sync_node(node.address)

        results = await asyncio.gather(
            *(_probe(n) for n in nodes),
            return_exceptions=True,
        )

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        from .notifications import notification_service

        for node, outcome in zip(nodes, results):
            # outcome is either Dict, None, or an Exception
            is_up = isinstance(outcome, dict)

            # Alert on status change to offline
            if not is_up and node.status == "online":
                await notification_service.notify("critical", node.name, "Node went OFFLINE! 🔴")
            elif is_up and node.status == "offline":
                await notification_service.notify("info", node.name, "Node is back ONLINE! 🟢")

            node.status = "online" if is_up else "offline"
            node.last_seen = now

            if is_up:
                if outcome.get("provider"):
                    # Autodiscovery: update the node's provider type based on what
                    # the agent reports. This allows registering as 'agent' and
                    # having the master figure out it's actually 'wireguard'.
                    node.provider_type = outcome["provider"]

                # Task 6: Collect metrics
                metrics = outcome.get("metrics", {})
                cpu_ema = metrics.get("cpu_usage_percent", 0.0)
                mem_usage = metrics.get("memory_usage_percent")
                disk_usage = metrics.get("disk_usage_percent")
                temp = metrics.get("temperature")
                rx_bps = metrics.get("rx_bps", 0.0)
                tx_bps = metrics.get("tx_bps", 0.0)

                stat = NodeStat(
                    node_id=node.id,
                    cpu_ema=cpu_ema,
                    memory_usage=mem_usage,
                    disk_usage=disk_usage,
                    rx_bps=rx_bps,
                    tx_bps=tx_bps,
                    timestamp=now,
                )
                self.db.add(stat)

                # Check for alerts
                if cpu_ema > 90.0:
                    await notification_service.notify(
                        "warning", node.name, f"High CPU usage: {cpu_ema:.1f}%"
                    )
                if mem_usage and mem_usage > 90.0:
                    await notification_service.notify(
                        "warning", node.name, f"High Memory usage: {mem_usage:.1f}%"
                    )
                if disk_usage and disk_usage > 90.0:
                    await notification_service.notify(
                        "critical", node.name, f"Critical Disk space: {disk_usage:.1f}% left"
                    )
                if temp and temp > 80.0:
                    await notification_service.notify(
                        "warning", node.name, f"High Temperature detected: {temp:.1f}°C"
                    )

                await self.db.flush()

                # Prune old stats: keep only last 20
                # We do this per node to be safe.
                # Find IDs of stats to keep (top 20 newest)
                subq = (
                    select(NodeStat.id)
                    .where(NodeStat.node_id == node.id)
                    .order_by(NodeStat.timestamp.desc())
                    .limit(20)
                )
                ids_result = await self.db.execute(subq)
                ids_to_keep = ids_result.scalars().all()

                if len(ids_to_keep) >= 20:
                    await self.db.execute(
                        delete(NodeStat)
                        .where(NodeStat.node_id == node.id)
                        .where(NodeStat.id.not_in(ids_to_keep))
                    )

        await self.db.commit()
