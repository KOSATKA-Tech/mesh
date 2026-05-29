import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from ..config import settings

logger = logging.getLogger("kosatka_master.email")


async def send_email(to_email: str, subject: str, body: str):
    """Send an email using SMTP settings from config."""
    if not settings.smtp_host:
        logger.warning("SMTP not configured, skipping email.")
        return

    msg = MIMEMultipart()
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html"))

    try:
        # Standard smtplib is blocking, but for notifications it's usually acceptable
        # or we could wrap it in run_in_executor
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            if settings.smtp_user and settings.smtp_password:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        logger.info(f"Email sent to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
