"""Server-side transactional email for administrator-created accounts."""
import asyncio
import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings
from app.core.errors import ValidationError


class EmailService:
    @staticmethod
    def _configured() -> bool:
        return bool(settings.SMTP_HOST and settings.SMTP_FROM_EMAIL)

    async def send_user_invitation(self, *, recipient: str, full_name: str, role: str, temporary_password: str) -> None:
        if not self._configured():
            raise ValidationError("Invitation email is not configured. Set SMTP_HOST and SMTP_FROM_EMAIL server-side before creating users.")

        message = EmailMessage()
        message["Subject"] = "Your BlogPilot account invitation"
        message["From"] = settings.SMTP_FROM_EMAIL
        message["To"] = recipient
        message.set_content(
            f"Hello {full_name},\n\n"
            f"An administrator created your BlogPilot {role.replace('_', ' ').title()} account.\n\n"
            f"Sign in: {settings.APP_PUBLIC_URL.rstrip('/')}/login\n"
            f"Temporary password: {temporary_password}\n\n"
            "Keep this temporary password private.\n\n"
            "— BlogPilot"
        )
        await asyncio.to_thread(self._send, message)

    @staticmethod
    def _send(message: EmailMessage) -> None:
        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT_SECONDS) as client:
                if settings.SMTP_USE_TLS:
                    client.starttls(context=ssl.create_default_context())
                if settings.SMTP_USERNAME:
                    client.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD or "")
                client.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            raise ValidationError("Invitation email could not be delivered. Verify the server-side SMTP configuration.") from exc
