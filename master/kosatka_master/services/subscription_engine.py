import logging
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..agent_client import call_agent
from ..models.client import Client
from ..models.node import Node
from ..models.subscription import Subscription

logger = logging.getLogger(__name__)


class SubscriptionEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_subscription(self, client_id: int, plan_name: str, expires_at: datetime):
        subscription = Subscription(client_id=client_id, plan_name=plan_name, expires_at=expires_at)
        self.db.add(subscription)

        # Ensure client is active when a subscription is added
        result = await self.db.execute(select(Client).where(Client.id == client_id))
        client = result.scalar_one_or_none()
        if client:
            client.is_active = True

        await self.db.commit()
        await self.db.refresh(subscription)
        return subscription

    async def check_expirations(self):
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # 1. Identify and deactivate expired subscriptions
        query = (
            update(Subscription)
            .where(Subscription.expires_at < now)
            .where(Subscription.is_active.is_(True))
            .values(is_active=False)
        )
        await self.db.execute(query)
        await self.db.commit()

        # 2. Find clients that no longer have ANY active subscriptions
        # and are still marked as active.
        clients_query = select(Client).where(Client.is_active.is_(True))
        result = await self.db.execute(clients_query)
        active_clients = result.scalars().all()

        for client in active_clients:
            sub_query = (
                select(Subscription)
                .where(Subscription.client_id == client.id)
                .where(Subscription.is_active.is_(True))
            )
            sub_result = await self.db.execute(sub_query)
            if not sub_result.scalar_one_or_none():
                logger.info(
                    f"Client {client.external_id} (id={client.id}) has no active subscriptions. Deactivating."
                )
                client.is_active = False

                # If we know which node the client is on, revoke access on the agent
                if client.node_id:
                    node_res = await self.db.execute(select(Node).where(Node.id == client.node_id))
                    node = node_res.scalar_one_or_none()
                    if node:
                        try:
                            await call_agent(node, "DELETE", f"/clients/{client.external_id}")
                            logger.info(
                                f"Successfully revoked access for {client.external_id} on agent {node.name}"
                            )
                        except Exception as exc:
                            logger.error(
                                f"Failed to revoke access for {client.external_id} on agent {node.name}: {exc}"
                            )

        await self.db.commit()
