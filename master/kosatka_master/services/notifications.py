import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.alert import SystemAlert

logger = logging.getLogger("kosatka_master.notifications")


class NotificationService:
    def __init__(self, db: AsyncSession | None = None):
        self.db = db

    async def notify(self, level: str, source: str, message: str):
        logger.warning(f"ALERT [{level}] from {source}: {message}")

        # 1. Write to DB if session provided
        if self.db:
            alert = SystemAlert(level=level, source=source, message=message)
            self.db.add(alert)
            await self.db.commit()

        # 2. Webhook Fallback
        if settings.webhook_url:
            async with httpx.AsyncClient() as client:
                try:
                    payload = {
                        "level": level,
                        "source": source,
                        "message": message,
                        "secret": settings.webhook_secret,
                    }
                    await client.post(settings.webhook_url, json=payload, timeout=5.0)
                except Exception as e:
                    logger.error(f"Failed to send webhook notification: {e}")


notification_service = NotificationService()
