"""
app/services/email_service.py
SMTP email delivery service for user invitations, registration approval requests,
and account activation notifications.
"""
from email.message import EmailMessage
import logging
import smtplib
from typing import Iterable

from ..core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Sends transactional emails via SMTP when configured in settings."""

    @staticmethod
    def is_configured() -> bool:
        return bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD)

    @staticmethod
    def send_email(
        to_email: str | Iterable[str],
        subject: str,
        text_body: str,
        html_body: str | None = None,
    ) -> bool:
        recipients = [to_email] if isinstance(to_email, str) else [e for e in to_email if e]
        if not recipients:
            return False

        if not EmailService.is_configured():
            logger.warning(
                "SMTP is not configured (set SMTP_USER and SMTP_PASSWORD in backend/.env). "
                "Skipping email '%s' to %s.",
                subject,
                ", ".join(recipients),
            )
            return False

        sender = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = f"Operix Platform <{sender}>"
        msg["To"] = ", ".join(recipients)
        msg.set_content(text_body)
        if html_body:
            msg.add_alternative(html_body, subtype="html")

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
                if settings.SMTP_USE_TLS:
                    server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            logger.info("Email '%s' delivered to %s.", subject, ", ".join(recipients))
            return True
        except Exception as exc:
            logger.error("Failed to send email '%s' to %s: %s", subject, ", ".join(recipients), exc)
            return False

    @staticmethod
    def send_invite_email(
        *,
        to_email: str,
        full_name: str,
        role_name: str,
        factory_name: str,
    ) -> bool:
        login_url = f"{settings.FRONTEND_APP_URL.rstrip('/')}/login"
        subject = f"You are invited to {factory_name} on Operix"
        text_body = (
            f"Hello {full_name},\n\n"
            f"You have been invited to join {factory_name} on Operix as {role_name}.\n"
            f"Sign in or complete your account setup at: {login_url}\n\n"
            f"Operix Industrial AI Safety Platform"
        )
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 560px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 10px;">
          <h2 style="color: #1e3a5f; margin-top: 0;">You're invited to Operix</h2>
          <p>Hello <strong>{full_name}</strong>,</p>
          <p>An administrator has invited you to join <strong>{factory_name}</strong> as <strong>{role_name}</strong>.</p>
          <p style="margin: 24px 0;">
            <a href="{login_url}" style="background: #1e3a5f; color: #fff; padding: 10px 18px; border-radius: 6px; text-decoration: none; font-weight: 600;">
              Open Operix
            </a>
          </p>
          <p style="color: #64748b; font-size: 12px;">If you weren't expecting this invitation, you can ignore this email.</p>
        </div>
        """
        return EmailService.send_email(to_email, subject, text_body, html_body)

    @staticmethod
    def send_registration_request_to_admins(
        *,
        admin_emails: list[str],
        applicant_name: str,
        applicant_email: str,
        role_name: str,
        factory_name: str,
    ) -> bool:
        review_url = f"{settings.FRONTEND_APP_URL.rstrip('/')}/settings/users"
        subject = f"[Operix] New account approval request: {applicant_name}"
        text_body = (
            f"Hello Administrator,\n\n"
            f"A new user has requested an account on Operix ({factory_name}):\n"
            f"- Name: {applicant_name}\n"
            f"- Email: {applicant_email}\n"
            f"- Requested Role: {role_name}\n\n"
            f"Please review and approve or reject this request in Users & Roles:\n"
            f"{review_url}\n"
        )
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 560px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 10px;">
          <h2 style="color: #1e3a5f; margin-top: 0;">New Account Approval Request</h2>
          <p>A new user has registered and is waiting for your approval to access <strong>{factory_name}</strong>:</p>
          <ul style="line-height: 1.7;">
            <li><strong>Name:</strong> {applicant_name}</li>
            <li><strong>Email:</strong> {applicant_email}</li>
            <li><strong>Requested Role:</strong> {role_name}</li>
          </ul>
          <p style="margin: 24px 0;">
            <a href="{review_url}" style="background: #1e3a5f; color: #fff; padding: 10px 18px; border-radius: 6px; text-decoration: none; font-weight: 600;">
              Review in Users &amp; Roles
            </a>
          </p>
        </div>
        """
        return EmailService.send_email(admin_emails, subject, text_body, html_body)

    @staticmethod
    def send_account_approved_email(
        *,
        to_email: str,
        full_name: str,
        role_name: str,
        factory_name: str,
    ) -> bool:
        login_url = f"{settings.FRONTEND_APP_URL.rstrip('/')}/login"
        subject = f"Your Operix account for {factory_name} has been approved"
        text_body = (
            f"Hello {full_name},\n\n"
            f"Your Operix account for {factory_name} ({role_name}) has been approved by an administrator.\n"
            f"You can now sign in at: {login_url}\n"
        )
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 560px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 10px;">
          <h2 style="color: #15803d; margin-top: 0;">Account Approved</h2>
          <p>Hello <strong>{full_name}</strong>,</p>
          <p>Your account for <strong>{factory_name}</strong> (role: <strong>{role_name}</strong>) has been approved.</p>
          <p style="margin: 24px 0;">
            <a href="{login_url}" style="background: #1e3a5f; color: #fff; padding: 10px 18px; border-radius: 6px; text-decoration: none; font-weight: 600;">
              Sign in to Operix
            </a>
          </p>
        </div>
        """
        return EmailService.send_email(to_email, subject, text_body, html_body)
