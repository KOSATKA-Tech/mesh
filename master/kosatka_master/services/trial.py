import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..agent_client import call_agent
from ..config import settings
from ..models.client import Client
from ..models.node import Node
from .email import send_email

logger = logging.getLogger("kosatka_master.trial")


class TrialService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def request_trial(self, email: str) -> bool:
        """
        Processes a trial request:
        1. Creates a temporary client.
        2. Picks an active exit node.
        3. Provisions the client on the node.
        4. Sends the email with the config and instructions.
        """
        # 1. Check if email already had a trial (optional, for now just allow)
        # 2. Create client
        external_id = f"trial_{email.replace('@', '_at_')}"

        # Check if already exists
        res = await self.db.execute(select(Client).where(Client.email == email))
        client = res.scalar_one_or_none()

        if client:
            if not client.is_trial:
                logger.info(f"User with email {email} already has a full account.")
                return False
            # If trial exists, we can extend it or just resend
        else:
            client = Client(
                external_id=external_id,
                email=email,
                is_trial=True,
                expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=3),
            )
            self.db.add(client)
            await self.db.commit()
            await self.db.refresh(client)

        # 3. Pick an active node (prefer xray/vless for trials)
        nodes_q = await self.db.execute(
            select(Node).where(Node.is_active.is_(True), Node.role == "exit")
        )
        nodes = nodes_q.scalars().all()
        if not nodes:
            logger.error("No active exit nodes available for trial provisioning.")
            return False

        # Simple pick for now
        node = nodes[0]

        # 4. Provision on agent
        try:
            agent_payload = {"external_id": client.external_id, "email": client.email}
            agent_result = await call_agent(node, "POST", "/clients", json=agent_payload)
            config_text = agent_result.get("config_text") or ""

            if not config_text:
                # Try fallback
                follow_up = await call_agent(node, "GET", f"/clients/{client.external_id}/config")
                config_text = follow_up.get("config", "")

            if not config_text:
                logger.error(f"Failed to get config for trial user {email}")
                return False

            # Update client with node_id
            client.node_id = node.id
            await self.db.commit()

            # 5. Send email
            subject = "🦈 KOSATKA: Ваш экстренный доступ на 3 часа"
            body = self._generate_email_body(email, config_text)
            await send_email(email, subject, body)

            return True
        except Exception as e:
            logger.error(f"Trial provisioning failed for {email}: {e}")
            return False

    def _generate_email_body(self, email: str, config: str) -> str:
        bot_link = f"https://t.me/{settings.bot_username}?start=trial_{email.replace('@', '_at_')}"

        return f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
            <h2 style="color: #000;">🐋 KOSATKA Mesh: Экстренный доступ</h2>
            <p>Мы активировали для вас временный доступ к VPN на 3 часа, чтобы вы могли зайти в Telegram и оформить полноценную подписку.</p>

            <div style="background: #f4f4f4; padding: 15px; border-radius: 10px; margin: 20px 0;">
                <code style="word-break: break-all; font-size: 12px;">{config}</code>
            </div>

            <h3>🚀 Что делать дальше?</h3>
            <ol>
                <li>Скопируйте код выше.</li>
                <li>Установите приложение <b>V2RayNG</b> (Android), <b>v2Box</b> (iOS) или <b>v2rayN</b> (Windows).</li>
                <li>Импортируйте конфиг из буфера обмена.</li>
                <li>Подключитесь к VPN.</li>
                <li><b>Нажмите на кнопку ниже, чтобы перейти в бот и закрепить доступ:</b></li>
            </ol>

            <a href="{bot_link}" style="display: inline-block; background: #0088cc; color: #fff; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold; margin-top: 10px;">Перейти в Telegram Бота 🦈</a>

            <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
            <p style="font-size: 12px; color: #666;">Это автоматическое письмо. Не отвечайте на него.</p>
        </div>
        """
