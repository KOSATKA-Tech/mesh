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
            subject = "🦈 KOSATKA // TRIAL UPLINK ACTIVE"
            body = self._generate_email_body(email, config_text)
            await send_email(email, subject, body)

            return True
        except Exception as e:
            logger.error(f"Trial provisioning failed for {email}: {e}")
            return False

    def _generate_email_body(self, email: str, config: str) -> str:
        bot_link = f"https://t.me/{settings.bot_username}?start=trial_{email.replace('@', '_at_')}"

        return f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ margin: 0; padding: 0; background-color: #000000; color: #FFFFFF; font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 60px 40px; background-color: #02060A; border: 1px solid rgba(255,255,255,0.05); }}
        .logo {{ width: 140px; margin-bottom: 50px; opacity: 0.9; }}
        h1 {{ font-size: 22px; font-weight: 900; letter-spacing: 0.3em; text-transform: uppercase; font-style: italic; margin-bottom: 30px; color: #FFFFFF; }}
        p {{ font-size: 14px; line-height: 1.8; color: rgba(255,255,255,0.5); margin-bottom: 30px; letter-spacing: 0.02em; }}
        .config-box {{ background-color: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; padding: 25px; margin-bottom: 40px; word-break: break-all; font-family: 'Courier New', monospace; font-size: 11px; color: rgba(255,255,255,0.7); line-height: 1.5; }}
        .button {{ display: inline-block; background-color: #FFFFFF; color: #000000; padding: 20px 40px; border-radius: 16px; text-decoration: none; font-weight: 900; font-size: 11px; text-transform: uppercase; letter-spacing: 0.3em; transition: all 0.3s; box-shadow: 0 10px 30px rgba(255,255,255,0.1); }}
        .footer {{ margin-top: 80px; padding-top: 30px; border-top: 1px solid rgba(255,255,255,0.05); font-size: 9px; color: rgba(255,255,255,0.2); letter-spacing: 0.2em; text-transform: uppercase; text-align: center; }}
        .step {{ margin-bottom: 25px; }}
        .step-title {{ display: block; font-weight: 900; color: rgba(255,255,255,0.3); margin-bottom: 8px; text-transform: uppercase; font-size: 10px; letter-spacing: 0.4em; }}
        .step-desc {{ font-size: 13px; color: rgba(255,255,255,0.6); margin: 0; }}
    </style>
</head>
<body>
    <div class="container">
        <img src="https://raw.githubusercontent.com/KOSATKA-Tech/mesh/main/assets/kosatka-mesh-site-logo.png" alt="KOSATKA" class="logo" />

        <h1>Trial Access Active</h1>

        <p>We have initialized your 3-hour high-speed session. Use the access protocol below to establish a secure connection and finalize your deployment in Telegram.</p>

        <div class="config-box">{config}</div>

        <div class="step">
            <span class="step-title">Protocol 01</span>
            <p class="step-desc">Install <b>v2Box</b> (iOS), <b>V2RayNG</b> (Android), or <b>v2rayN</b> (Windows).</p>
        </div>

        <div class="step">
            <span class="step-title">Protocol 02</span>
            <p class="step-desc">Import the cryptographic uplink code provided above into your client application.</p>
        </div>

        <div class="step">
            <span class="step-title">Protocol 03</span>
            <p class="step-desc">Execute the connection and proceed to our Telegram storefront to secure permanent access.</p>
        </div>

        <div style="text-align: center; margin-top: 50px;">
            <a href="{bot_link}" class="button">Open Telegram Bot</a>
        </div>

        <div class="footer">
            System Protocol // KOSATKA Technologies // 2026
        </div>
    </div>
</body>
</html>
"""
