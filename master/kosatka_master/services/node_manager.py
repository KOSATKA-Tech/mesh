import asyncio
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.node import Node
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
        # multiplied the worst-case sync latency by N \u2014 with default
        # ``KOSATKA_SYNC_INTERVAL=60`` and a single dead node taking 5s
        # to time out, ten nodes alone could blow past the next tick and
        # starve the scheduler. ``return_exceptions=True`` keeps one
        # misbehaving agent from short-circuiting the rest.
        async def _probe(node: Node) -> Dict[str, Any] | None:
            key = node.api_key or settings.effective_agent_api_key()
            provider = AgentNodeProvider(key)
            return await provider.sync_node(node.address)

        results = await asyncio.gather(
            *(_probe(n) for n in nodes),
            return_exceptions=True,
        )

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for node, outcome in zip(nodes, results):
            # outcome is either Dict, None, or an Exception
            is_up = isinstance(outcome, dict)
            node.status = "online" if is_up else "offline"
            node.last_seen = now

            if is_up and outcome.get("provider"):
                # Autodiscovery: update the node's provider type based on what
                # the agent reports. This allows registering as 'agent' and
                # having the master figure out it's actually 'wireguard'.
                node.provider_type = outcome["provider"]

        await self.db.commit()
