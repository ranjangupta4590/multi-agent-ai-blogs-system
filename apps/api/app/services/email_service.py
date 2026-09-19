"""Server-side transactional email with BlogPilot website-themed HTML templates."""
import asyncio
import smtplib
import ssl
from email.message import EmailMessage
from typing import Optional

from app.core.config import settings
from app.core.errors import ValidationError
from app.core.logging import logger


class EmailService:
    @staticmethod
    def _configured() -> bool:
        return bool(settings.SMTP_HOST and settings.SMTP_FROM_EMAIL)

    @staticmethod
    def _wrap_html_template(*, title: str, status_badge: str, status_badge_color: str, status_badge_bg: str, content_html: str, cta_text: Optional[str] = None, cta_url: Optional[str] = None) -> str:
        """Wrap email body in BlogPilot's sleek website theme design system."""
        cta_button_html = ""
        if cta_text and cta_url:
            cta_button_html = f"""
            <div style="text-align: center; margin: 32px 0 16px 0;">
                <a href="{cta_url}" style="display: inline-block; background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); color: #ffffff; text-decoration: none; font-size: 15px; font-weight: 700; padding: 14px 32px; border-radius: 28px; box-shadow: 0 4px 14px rgba(79, 70, 229, 0.35);">
                    {cta_text} &rarr;
                </a>
            </div>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; color: #1e293b;">
    <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #f8fafc; padding: 40px 16px;">
        <tr>
            <td align="center">
                <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 580px; background-color: #ffffff; border-radius: 18px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.04);">
                    <!-- Brand Gradient Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #0ea5e9 0%, #6366f1 50%, #8b5cf6 100%); padding: 28px 32px; text-align: left;">
                            <div style="display: inline-flex; align-items: center; gap: 8px;">
                                <span style="font-size: 22px; color: #ffffff; font-weight: 800; line-height: 1;">✦ BlogPilot</span>
                                <span style="background: rgba(255, 255, 255, 0.2); color: #ffffff; font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 12px; text-transform: uppercase; margin-left: 8px; letter-spacing: 0.05em;">AI Studio</span>
                            </div>
                            <h1 style="color: #ffffff; font-size: 22px; font-weight: 800; margin: 16px 0 0 0; letter-spacing: -0.02em;">
                                {title}
                            </h1>
                        </td>
                    </tr>

                    <!-- Body Content -->
                    <tr>
                        <td style="padding: 32px 32px 24px 32px;">
                            <div style="display: inline-block; background-color: {status_badge_bg}; color: {status_badge_color}; font-size: 12px; font-weight: 800; padding: 4px 12px; border-radius: 16px; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 0.04em;">
                                {status_badge}
                            </div>

                            <div style="font-size: 15px; line-height: 1.6; color: #334155;">
                                {content_html}
                            </div>

                            {cta_button_html}
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f1f5f9; padding: 20px 32px; border-top: 1px solid #e2e8f0; text-align: center;">
                            <p style="margin: 0; font-size: 12px; color: #64748b;">
                                &copy; 2026 BlogPilot Systems &bull; Multi-Agent AI Studio Platform
                            </p>
                            <p style="margin: 6px 0 0 0; font-size: 11px; color: #94a3b8;">
                                Automated notification from your studio workspace.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

    async def send_user_invitation(self, *, recipient: str, full_name: str, role: str, temporary_password: str) -> None:
        login_url = f"{settings.APP_PUBLIC_URL.rstrip('/')}/login"
        content_html = f"""
        <p>Hello <strong>{full_name}</strong>,</p>
        <p>An administrator created your BlogPilot <strong>{role.replace('_', ' ').title()}</strong> account.</p>
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px; margin: 20px 0;">
            <p style="margin: 0 0 8px 0; font-size: 13px; color: #64748b;">Sign in with your temporary password:</p>
            <code style="font-size: 16px; font-weight: 700; color: #4f46e5; background: #eef2ff; padding: 4px 10px; border-radius: 6px; display: inline-block;">
                {temporary_password}
            </code>
        </div>
        <p style="font-size: 13px; color: #64748b;">Please keep this temporary password confidential.</p>
        """
        html = self._wrap_html_template(
            title="Your Account Invitation",
            status_badge="Account Created",
            status_badge_color="#4f46e5",
            status_badge_bg="#eef2ff",
            content_html=content_html,
            cta_text="Sign In to Studio",
            cta_url=login_url,
        )
        await self._send_email(
            recipient=recipient,
            subject="Your BlogPilot Account Invitation",
            plain_text=f"Hello {full_name},\n\nSign in at {login_url}\nTemporary password: {temporary_password}",
            html_content=html,
        )

    async def send_subscription_activated_email(
        self,
        *,
        recipient: str,
        company_name: str,
        plan_name: str,
        expires_at_str: str,
        amount_str: str = "",
    ) -> None:
        """Triggered upon successful payment capture or webhook unfreeze."""
        studio_url = f"{settings.APP_PUBLIC_URL.rstrip('/')}/dashboard"
        amount_notice = f"<p><strong>Amount Paid:</strong> {amount_str}</p>" if amount_str else ""
        content_html = f"""
        <p>Great news! Payment for <strong>{company_name}</strong> has been successfully captured and verified.</p>
        <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 12px; padding: 18px; margin: 20px 0;">
            <p style="margin: 0 0 6px 0; font-size: 14px; color: #166534;"><strong>Plan:</strong> {plan_name}</p>
            <p style="margin: 0 0 6px 0; font-size: 14px; color: #166534;"><strong>Valid Until:</strong> {expires_at_str}</p>
            {amount_notice}
            <p style="margin: 8px 0 0 0; font-size: 13px; color: #15803d;">
                ✓ Studio workspace is fully unlocked and active.<br>
                ✓ All 11 specialist AI agent pipelines are active.
            </p>
        </div>
        <p>You can now continue researching, writing, and publishing with zero restrictions.</p>
        """
        html = self._wrap_html_template(
            title="Payment Confirmed & Studio Unlocked",
            status_badge="✓ Active & Unfrozen",
            status_badge_color="#15803d",
            status_badge_bg="#dcfce7",
            content_html=content_html,
            cta_text="Launch Studio Dashboard",
            cta_url=studio_url,
        )
        await self._send_email(
            recipient=recipient,
            subject=f"✓ Subscription Confirmed: {company_name} is Unlocked",
            plain_text=f"Payment for {company_name} confirmed. Plan: {plan_name}. Valid until: {expires_at_str}.\nAccess your studio at: {studio_url}",
            html_content=html,
        )

    async def send_workspace_frozen_email(
        self, *, recipient: str, company_name: str, reason: str
    ) -> None:
        """Triggered when subscription is halted, cancelled, or frozen via webhook / superadmin."""
        renew_url = f"{settings.APP_PUBLIC_URL.rstrip('/')}/admin/subscription"
        content_html = f"""
        <p>Notice regarding company workspace: <strong>{company_name}</strong>.</p>
        <div style="background-color: #fef2f2; border: 1px solid #fecaca; border-radius: 12px; padding: 18px; margin: 20px 0;">
            <p style="margin: 0 0 6px 0; font-size: 14px; color: #991b1b;">
                <strong>Reason:</strong> {reason}
            </p>
            <p style="margin: 8px 0 0 0; font-size: 13px; color: #b91c1c;">
                🔒 Workspace access has been temporarily suspended.<br>
                🔒 Autonomous agent runs, article drafting, and CMS syndication are paused.
            </p>
        </div>
        <p>Your workspace data and drafts are safely preserved. To restore access instantly, please renew your subscription using the link below.</p>
        """
        html = self._wrap_html_template(
            title="Workspace Frozen: Subscription Suspended",
            status_badge="🔒 Workspace Frozen",
            status_badge_color="#b91c1c",
            status_badge_bg="#fee2e2",
            content_html=content_html,
            cta_text="⚡ Renew Plan & Restore Access",
            cta_url=renew_url,
        )
        await self._send_email(
            recipient=recipient,
            subject=f"🔒 Action Required: {company_name} Workspace Frozen",
            plain_text=f"Workspace for {company_name} has been frozen. Reason: {reason}.\nRestore access at: {renew_url}",
            html_content=html,
        )

    async def send_payment_failed_email(
        self, *, recipient: str, company_name: str, failure_reason: str
    ) -> None:
        """Triggered when a recurring or checkout payment attempt fails."""
        retry_url = f"{settings.APP_PUBLIC_URL.rstrip('/')}/admin/subscription"
        content_html = f"""
        <p>We attempted to process your subscription renewal for <strong>{company_name}</strong>, but the transaction could not be completed.</p>
        <div style="background-color: #fffbeb; border: 1px solid #fde68a; border-radius: 12px; padding: 18px; margin: 20px 0;">
            <p style="margin: 0 0 6px 0; font-size: 14px; color: #92400e;">
                <strong>Gateway Notice:</strong> {failure_reason}
            </p>
            <p style="margin: 8px 0 0 0; font-size: 13px; color: #b45309;">
                ⚠️ To prevent your workspace from being suspended, please update your payment details or retry the payment.
            </p>
        </div>
        <p>You can retry your payment directly from your subscription console.</p>
        """
        html = self._wrap_html_template(
            title="Payment Failed: Renewal Required",
            status_badge="⚠️ Payment Unsuccessful",
            status_badge_color="#b45309",
            status_badge_bg="#fef3c7",
            content_html=content_html,
            cta_text="Retry Payment Now",
            cta_url=retry_url,
        )
        await self._send_email(
            recipient=recipient,
            subject=f"⚠️ Payment Failed: Action Required for {company_name}",
            plain_text=f"Payment for {company_name} failed. Reason: {failure_reason}.\nRetry at: {retry_url}",
            html_content=html,
        )

    async def _send_email(self, *, recipient: str, subject: str, plain_text: str, html_content: str) -> None:
        if not self._configured():
            logger.warning(
                f"[SMTP NOT CONFIGURED - DEV MODE] Email would be sent to: {recipient} | Subject: {subject}"
            )
            return

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = settings.SMTP_FROM_EMAIL
        message["To"] = recipient
        message.set_content(plain_text)
        message.add_alternative(html_content, subtype="html")

        try:
            await asyncio.to_thread(self._send, message)
        except Exception as err:
            logger.error(f"Failed to deliver email to {recipient}: {err}")

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
            raise ValidationError("Email delivery failed. Verify server-side SMTP configuration.") from exc
